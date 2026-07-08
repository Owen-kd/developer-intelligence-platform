# ADR-011 — Redis 기반 EventBus (다중 프로세스 상시 구동)

- 상태: Accepted
- 날짜: 2026-07-08
- 관련: [ADR-003](ADR-003-eventbus.md)(EventBus 포트) · [target-service](../planning/target-service.md) · [ADR-009]

## 맥락
24시간 상시 서비스(target-service)는 **scheduler(생산자)** 와 **worker(소비자)** 가 별도 프로세스로 상시 떠 있어야 한다.
현 `InMemoryEventBus` 는 인프로세스 전용 — 발행과 구독이 같은 프로세스여야만 동작한다. 프로세스를 넘는 이벤트 전달이 불가.
ADR-003 이 이미 "이후 Redis/브로커 백엔드로 교체 가능하도록 인터페이스 유지"를 예고했다.

## 결정
`EventBus` 포트(dip_platform)를 구현하는 **`RedisEventBus`** 를 `infrastructure/redis/` 에 추가한다
(`PostgresEventStore` 가 platform 포트를 infrastructure 에서 구현하는 것과 동일한 포트-어댑터 선례).

- **전송 = Redis Streams**(`XADD`/`XREADGROUP`) — 소비자 그룹 + 확인(ack)으로 유실 방지·수평 확장.
- **직렬화** — 이벤트를 `{name, event_id, occurred_at, payload(JSON)}` 로 스트림에 적재.
  소비 측은 payload 를 일반 객체(속성 접근)로 복원한다. 핸들러는 `getattr(payload, ...)` 를 쓰므로 타입 재구성 불필요.
- **구독 = 로컬 등록**(포트 그대로) + `run()` 소비 루프가 스트림을 읽어 로컬 핸들러에 격리 디스패치(한 핸들러 실패가 다른 핸들러를 막지 않음 — InMemory 와 동일 계약).
- `store` 주입 시 발행 전에 append-only 적재(기존과 동일).
- 라이브러리 = `redis`(redis-py, asyncio 내장). 설정 `redis_url`.

## 근거
- Streams: pub/sub 과 달리 **영속**(소비자 없을 때도 유실 없음) + 소비자 그룹으로 worker 여러 개 확장.
- 포트 불변 → 조립만 InMemory→Redis 로 교체, modules/platform 코드 0 변경.
- payload 를 일반 객체로 복원 → 프로세스 간 페이로드 클래스 공유/등록 불필요(현 핸들러가 속성 접근만 함).

## 절충 / 리스크
- payload 복원이 일반 객체라 타입 안전성은 약함(핸들러가 속성 접근 규약을 지켜야). 강타입이 필요하면 name→payload 클래스 레지스트리 후속.
- 정확히-한번(exactly-once) 아님 — at-least-once + 멱등 핸들러(기존 설계가 멱등 지향)로 대응.
- 스트림 트리밍/보존정책, DLQ(죽은편지)는 후속(초기엔 단순 ack).
- InMemoryEventBus 는 테스트/단일프로세스 데모에 계속 사용.

## 결과
- `pyproject.toml`: `redis` 의존성. `shared/config/settings.py`: `redis_url`.
- `infrastructure/redis/event_bus.py`: `RedisEventBus(EventBus)` + `run()` 소비 루프.
- 상시 worker 진입점(apps.worker)이 이 버스로 scheduler 와 분리 구동([target-service] #4/#5).
- 라이브 검증: docker `redis:7` + 발행→소비 왕복 스모크.
