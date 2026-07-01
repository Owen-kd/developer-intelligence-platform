# ADR-003 — 모듈 간 통신에 EventBus 채택

- 상태: Accepted
- 날짜: 2026-07-01
- 관련: [../architecture/event-flow.md](../architecture/event-flow.md)

## 맥락
Modular Monolith에서 모듈이 서로를 직접 import하면 결합이 커지고, 나중에 서비스로 분리하기 어렵다.
이슈 인입 하나가 comment/git/context/agent 여러 반응을 유발하는 팬아웃 구조가 필요하다.

## 결정
모듈 간 통신은 `platform/event` 의 **EventBus(publish/subscribe)** 를 1차 수단으로 한다.
동기 강결합이 꼭 필요한 경우에만 명시적 서비스 인터페이스를 쓰고, 이유를 남긴다.

## 근거
- 결합도 감소 → 각 모듈을 독립적으로 개발/테스트/분리 가능.
- 팬아웃 자연스러움 → 하나의 이벤트에 여러 구독자.
- 백엔드 교체 용이 → 초기 in-memory, 이후 Redis/브로커로 인터페이스 유지 교체.

## 절충 / 리스크
- 추적/디버깅이 동기 호출보다 어렵다 → `platform/audit` 로 이벤트 감사 로그 필수.
- 최종 일관성 → 핸들러 멱등성 요구, 재시도 전략 필요.
- 초기 in-memory는 프로세스 경계를 못 넘음 → 분산 필요 시점에 브로커 백엔드 도입.

## 결과
- 인터페이스: `publish(event)`, `subscribe(EventType, handler)`.
- 이벤트명 과거형 PascalCase, 페이로드는 불변 최소 DTO.
- 핸들러는 멱등, 실패 격리.
