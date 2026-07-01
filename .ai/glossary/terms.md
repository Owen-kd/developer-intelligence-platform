# Glossary — 용어 정의 (정본)

> DIP에서 쓰는 용어의 **단일 정의처(Single Source of Truth for vocabulary)**.
> 다른 문서는 용어를 재정의하지 말고 이 문서를 참조한다.

## 데이터 · 지식 계층

### Issue
외부 이슈 트래커(Jira 등)의 이슈. DIP에서는 원천 데이터의 대표적 진입점이며, 자체 Timeline을 가진다.

### Incident
서비스에 영향을 준 장애 사건. 대응·회고의 대상이며, 정제되면 Incident Library의 지식이 된다.

### Timeline
하나의 엔티티(Issue/Incident 등)에 대해 시간 순으로 쌓인 **Event의 나열**. 덮어쓰지 않고 append-only로 확장된다.

### Event
"무슨 일이 있었다"를 나타내는 **불변(immutable) 기록**. 과거형 이름을 가진다(`IssueCreated`). 모든 중요한 변화의 최소 단위이며 Knowledge의 원료다. → [event-contract](../contracts/event-contract.md)

### Knowledge
Event/Timeline으로부터 **정제(Promotion)된 재사용 가능한 지식**. AI가 소비하는 대상. 원천 데이터가 아니다. → [knowledge-contract](../contracts/knowledge-contract.md)

### Knowledge Library
축적된 Knowledge의 저장소. 플랫폼이 시간이 지날수록 똑똑해지는 자산.

### Root Cause
Incident의 근본 원인. 사실(Event)에 근거해 도출되며 Knowledge로 기록된다.

### Incident Library
Incident에서 도출된 Knowledge(근본 원인·해결·재발방지)의 축적된 라이브러리. Knowledge로부터 승격되어 생성된다.

### Promotion
하위 계층을 상위의 재사용 가능한 자산으로 **승격**하는 과정.
`Event/Timeline → Knowledge`, `Knowledge → Incident Library`.

## 파이프라인 · 실행

### Collector
외부 시스템(Jira/Git 등)에서 원천 데이터를 수집하는 컴포넌트. `infrastructure/` 를 경유하며, 수집 결과를 Event로 표현한다.

### Context
특정 작업(Triage/Impact 등)을 위해 **조립된 LLM 입력**. Knowledge를 기반으로 만들어진다.

### Context Builder
LLM 호출 **전에** Context를 조립하는 컴포넌트. 원천 데이터가 아니라 Knowledge를 입력으로 사용한다. → [context-engine](../architecture/context-engine.md)

### Agent
Context와 프롬프트 자산을 사용해 하나의 작업을 수행하는 LLM 기반 실행 단위. 외부 LLM 호출은 `infrastructure/` 를 경유한다. → [agent-contract](../contracts/agent-contract.md)

### Workflow
여러 Agent/단계의 **실행 순서를 오케스트레이션**하는 것. `platform/workflow`.

## 계층 간 흐름 요약
```
External → Collector → Event → Timeline
        → (Promotion) → Knowledge → Knowledge Library
        → (Promotion) → Incident Library
Knowledge → Context Builder → Context → Agent → Workflow → (새 Event/Knowledge)
```

## 관련 문서
- 철학: [../philosophy/](../philosophy/)
- 생명주기: [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md)
