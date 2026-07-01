# Contract — Event

> 모든 Event가 지켜야 하는 계약. Event는 DIP에서 역사와 지식의 원료다.

## 목적
"무슨 일이 있었다"를 불변으로 기록하고, 모듈 간 결합 없이 반응을 전파한다.

## 책임
- 하나의 의미 있는 사실을 표현한다.
- 구독자가 반응할 수 있도록 필요한 최소 정보를 전달한다.
- Timeline과 Knowledge 생성의 원료가 된다.

## Input (발행자 관점)
- 발행자: 상태를 바꾸는 대신 Event를 만든다.
- 페이로드: 식별자 + 반응에 필요한 최소 값(불변 DTO).

## Output (구독자 관점)
- `platform/event` EventBus가 등록된 핸들러에 전달.
- 핸들러는 자기 작업 수행 후 필요 시 새 Event를 발행(연쇄).

## Rules
- 이름: **과거형 PascalCase** — `IssueCreated`, `CommentAdded`, `IncidentDetected`.
- 페이로드: 불변 `<Event>Payload`. 거대한 객체 전체를 싣지 않는다(식별자 + 필요한 것).
- 핸들러는 **멱등(idempotent)** — 재전달돼도 결과가 같아야 한다.
- 한 핸들러의 실패가 다른 핸들러를 막지 않는다(격리) + 감사 로그(`platform/audit`).
- Event는 덮어쓰지 않는다(append-only). 정정이 필요하면 새 Event로.

## Example
```python
# 정의
@dataclass(frozen=True)
class IssueCreatedPayload:
    issue_id: str
    jira_key: str

# 발행
bus.publish(Event("IssueCreated", IssueCreatedPayload(issue_id, key)))

# 구독
bus.subscribe("IssueCreated", collect_comments_handler)  # 멱등 핸들러
```

## 관련
- [../philosophy/event-driven.md](../philosophy/event-driven.md) · [../architecture/event-flow.md](../architecture/event-flow.md) · [../decisions/ADR-003-eventbus.md](../decisions/ADR-003-eventbus.md)
