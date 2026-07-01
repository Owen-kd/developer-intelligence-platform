# Contract — Agent

> Agent가 지켜야 하는 계약. Agent는 파이프라인의 마지막 단계(AI Last)다.

## 목적
조립된 Context와 프롬프트 자산을 사용해 하나의 판단 작업(분류/영향도/원인분석 등)을 수행한다.

## 책임
- 주어진 Context 범위 안에서만 추론한다.
- 프롬프트 자산을 registry/파일에서 로드해 사용한다.
- 출력을 검증 가능한 구조로 반환한다.

## Input
- **Context** (Context Builder가 Knowledge 기반으로 조립한 것).
- **Prompt** 자산 (`prompts/`, `.ai/prompts/`, registry).
- 실행 파라미터(대상 식별자 등).

## Output
- 구조화된 결과(판정 + 근거 + 확신도).
- 필요 시 **Event** 발행(예: `ImpactAnalyzed`) → Knowledge로 승격 가능.

## Rules
- **Context Before AI.** Context 없이 LLM을 호출하지 않는다.
- 원천 데이터를 직접 받지 않는다 — 항상 Context를 통한다.
- 외부 LLM 호출은 `infrastructure/{openai,anthropic}` 를 경유한다(벤더 직접 호출 금지).
- 프롬프트를 코드에 하드코딩하지 않는다.
- **LLM 출력은 항상 검증**한다(스키마/파싱). 실패 시 재시도/폴백.
- 각 step의 입력/출력을 감사(`platform/audit`)에 남긴다.
- AI는 진실의 원천이 아니다. 결과는 검증 후 지식으로만 축적한다.

## Example
```
Trigger → Context Builder(Knowledge) → Context
        → Agent(prompt=triage/classify) → LLM(infrastructure)
        → 검증 → { category, priority, rationale } → IssueTriaged 발행
```

## 관련
- [../philosophy/context-over-prompt.md](../philosophy/context-over-prompt.md) · [../architecture/agent-flow.md](../architecture/agent-flow.md) · [../architecture/context-engine.md](../architecture/context-engine.md)
