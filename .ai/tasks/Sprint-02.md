# Sprint-02 — EventBus + 초기 스키마

- 상태: Todo
- Phase / Milestone: Phase 1 (Ingestion) / M1
- 의존성: Sprint-01(골격) — 완료
- 다음: Sprint-03 (Jira Collector)

## 문제 (Discovery)
모든 이후 파이프라인(수집→지식→컨텍스트→에이전트)은 두 가지 기반 위에 선다:
① 모듈 간 결합 없이 사실을 전파하는 **EventBus**, ② 사실을 불변으로 적재할 **DB 스키마**.
지금은 둘 다 설계·계약만 있고 코드가 없다([../state/current-architecture.md]).

## 범위
- 하는 것:
  - `platform/event`: `Event`, `<Event>Payload` 규약, `EventBus.publish/subscribe` 인터페이스 + **in-memory 구현**.
  - 핸들러 **격리**(한 핸들러 실패가 다른 핸들러를 막지 않음) + 실패 로깅 훅.
  - `database/migrations/001_init.sql`: `issues`, `comments`, `events` 테이블([../architecture/database-design.md]).
  - `apps/cli` 마이그레이션 적용 명령(또는 스크립트) 최소 경로.
- 안 하는 것(Non-goals):
  - Redis/브로커 백엔드(→ [APR-007]), commits/impact_reports 테이블(→ Sprint-04/10), 실제 이벤트 발행자.

## 성공 기준 (DoD)
- [ ] `bus.subscribe(...)` 후 `bus.publish(...)` 시 등록된 핸들러가 호출된다(unit test).
- [ ] 한 핸들러가 예외를 던져도 나머지 핸들러가 실행된다(격리 test).
- [ ] `001_init.sql` 적용 후 3개 테이블이 규약(복수형/`id`/`timestamptz`/`jsonb`)대로 생성된다.
- [ ] ruff / mypy(strict) / pytest 통과.

## 설계 메모 (Design)
- 배치: `platform/event`(플랫폼 코어). 의존성 방향 준수(누구도 상위를 import 안 함).
- 인터페이스: `EventBus`는 추상 → in-memory 구현이 첫 어댑터. 후속 Redis 교체 대비([../decisions/ADR-003-eventbus.md]).
- 이벤트 규약: 과거형 PascalCase, 불변 payload, **멱등 핸들러**([../contracts/event-contract.md]).
- 데이터: 스키마 변경은 `migrations/NNN_*.sql` 로만. 앱이 임의 DDL 금지.

## Approval Gate
- 없음(기반 작업, 신규 외부 의존성 없음).

## 체크리스트
- [ ] 구현 (event → migrations → cli)
- [ ] 테스트(격리/멱등 포함)
- [ ] 리뷰([../workflow/04-review.md])
- [ ] `current-task` / `state/current-architecture` 갱신

## 회고
- 잘된 것:
- 개선할 것:
