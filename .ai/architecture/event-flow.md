# Event Flow

## 왜 이벤트인가
모듈 간 직접 호출을 줄여 결합도를 낮추고, 각 모듈을 서비스로 분리 가능하게 유지한다.
결정 배경: [../decisions/ADR-003-eventbus.md](../decisions/ADR-003-eventbus.md)

## EventBus (platform/event)
```python
bus.publish(event)          # 이벤트 발행
bus.subscribe(EventType, handler)   # 구독 등록
```
- 초기: 인프로세스(in-memory) 동기/비동기 디스패치.
- 이후: Redis/브로커 백엔드로 교체 가능한 인터페이스 유지.

## 대표 흐름 — 이슈 인입
```
Scheduler(jira_sync) ──▶ IssueCreated
        │
        ├─▶ comment 모듈:  코멘트 수집 ─▶ CommentsCollected
        ├─▶ git 모듈:      관련 커밋 링크 ─▶ CommitsLinked
        └─▶ context:       Issue+Comment+Git 조립 ─▶ ContextAssembled
                    │
                    └─▶ workflow:  Triage/Impact Agent 실행 ─▶ ImpactAnalyzed
                                │
                                └─▶ api/report 로 노출
```

## 이벤트 규약
- 이름: 과거형 `PascalCase` (`IssueCreated`).
- 페이로드: 불변 DTO(`<Event>Payload`), 최소 식별자 + 필요한 값.
- 핸들러는 **멱등(idempotent)** 해야 한다(재전달 대비).
- 실패한 핸들러는 다른 핸들러를 막지 않는다(격리) + 감사 로그(`platform/audit`).

## 안티패턴
- 이벤트 페이로드에 거대한 객체 전체를 싣기 → 식별자+필요한 것만.
- 핸들러 안에서 또 다른 모듈을 직접 import → 필요한 데이터는 이벤트로.
