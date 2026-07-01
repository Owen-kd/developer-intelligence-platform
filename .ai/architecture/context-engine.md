# Architecture — Context Engine

> LLM 호출 전에 Knowledge로부터 Context를 조립하는 엔진(Context Builder)의 설계.
> 철학 근거: [../philosophy/context-over-prompt.md](../philosophy/context-over-prompt.md)
> 위치(예정): `platform/context`. 이 문서는 기존 `agent-flow.md`를 **구체화**한다.

## 목적
Agent가 사용할 **Context**를 Knowledge 기반으로 일관되게 조립한다. AI는 Context Before, AI Last.

## 위치
- `platform/context` (Context Builder). 데이터 수집은 모듈/인프라, 조립 오케스트레이션은 여기서.

## 입력 → 출력
```
입력:  작업 종류(triage/impact/...) + 대상 식별자(issue_id 등)
과정:  관련 Knowledge 조회 → 선별/랭킹 → 토큰 예산 내로 구성 → 출처 첨부
출력:  Context { task, target, knowledge[], sources[], budget_meta }
```

## 조립 규칙
- **원천 데이터가 아니라 Knowledge**를 입력으로 한다([knowledge-lifecycle.md]).
- 필요한 것만 담는다(토큰 예산 존중) — 신호 대 잡음비 우선.
- 출처(어떤 Knowledge/Event에서 왔는지)를 Context에 보존한다.
- 조립 규칙은 결정적이어야 한다 — 같은 입력 → 같은 Context(재현성).
- 프롬프트는 Context에 섞지 않는다. 프롬프트는 별도 자산(`prompts/`)로 Agent가 로드.

## Agent와의 경계
```
Context Builder ──(Context)──▶ Agent ──(prompt 자산)──▶ LLM(infrastructure)
```
- Context Builder는 "무엇을 알려줄지"를, Agent는 "무엇을 물을지"를 담당.
- LLM 벤더 교체는 infrastructure 계층에서 흡수되어 Context/Agent에 영향 없음.

## 관련
- [agent-flow.md](agent-flow.md) · [knowledge-lifecycle.md](knowledge-lifecycle.md)
- [../contracts/agent-contract.md](../contracts/agent-contract.md) · [../contracts/knowledge-contract.md](../contracts/knowledge-contract.md)
