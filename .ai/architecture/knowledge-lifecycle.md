# Architecture — Knowledge Lifecycle

> 원천 데이터가 어떻게 재사용 가능한 Knowledge로 승격되는가.
> 철학 근거: [../philosophy/knowledge-first.md](../philosophy/knowledge-first.md) · [../philosophy/event-driven.md](../philosophy/event-driven.md)
> 이 문서는 기존 설계를 **확장**하며, `event-flow.md`/`agent-flow.md`와 충돌하지 않는다(정제 계층을 명시할 뿐이다).

## 계층
```
External Systems (Jira, Git, ...)
        │  Collector (infrastructure 경유)
        ▼
      Event  ── append-only, 불변
        │
        ▼
     Timeline  ── 엔티티별 시간 축(Event 나열)
        │  Promotion
        ▼
    Knowledge  ── 정제·출처 보존 → Knowledge Library
        │  Promotion
        ▼
 Incident Library  ── 근본원인/해결/재발방지 지식
```

## 단계별 책임
| 단계 | 컴포넌트 | 하는 일 | 규칙 |
|------|----------|---------|------|
| 수집 | Collector (`infrastructure/*` + 모듈) | 외부 데이터 가져오기 | 외부 호출은 infrastructure 경유 |
| 기록 | Event (`platform/event`) | 사실을 불변으로 남김 | append-only, 과거형, 멱등 소비 |
| 축적 | Timeline | 엔티티별 Event 축적 | 덮어쓰기 금지 |
| 승격 1 | Promotion | Event/Timeline → Knowledge | 출처(Event) 보존, LLM 출력 검증 |
| 저장 | Knowledge Library | Knowledge 축적 | 재사용 가능한 형태 유지 |
| 승격 2 | Promotion | Knowledge → Incident Library | 근본원인은 사실 근거 필수 |

## 소비 측 (AI)
```
Knowledge → Context Builder → Context → Agent → (새 Event/Knowledge)
```
- **AI는 Knowledge를 소비한다. 원천 데이터를 직접 소비하지 않는다.**
- Agent의 산출물(분류/영향도/원인)은 다시 Event → Knowledge로 축적되어 복리로 쌓인다.

## 불변식 (Invariants)
1. Event는 절대 덮어쓰지 않는다.
2. 모든 Knowledge는 출처(Event/Knowledge)를 가진다.
3. LLM으로 생성된 Knowledge는 스키마 검증을 통과해야 저장된다.
4. Promotion은 파괴가 아니라 축적이다.

## 관련
- [context-engine.md](context-engine.md) · [event-flow.md](event-flow.md) · [agent-flow.md](agent-flow.md)
- [../contracts/knowledge-contract.md](../contracts/knowledge-contract.md) · [../contracts/event-contract.md](../contracts/event-contract.md)

> 참고: "AI는 Knowledge만 소비한다"를 프로젝트 **불변 규칙**으로 승격하려면 ADR이 적절하다(제안: ADR-004). 본 문서는 설계 설명이며 규칙 확정은 ADR로 분리한다.
