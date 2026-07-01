# Agent Flow

## 구성요소
- **registry** (`platform/registry`) — Agent와 Prompt를 등록/조회.
- **workflow** (`platform/workflow`) — Agent 실행 순서(오케스트레이션).
- **context** (`platform/context`) — 실행에 필요한 AI Context 조립.
- **infrastructure/{openai,anthropic}** — 실제 LLM 호출(모듈은 직접 호출 금지).

## 실행 파이프라인
```
Trigger(event/api)
   ↓
Context 조립  (Issue → Comment → Git → DB → Context)
   ↓
Playbook 선택 (.ai/playbooks/*)  ← AI는 Playbook을 가장 잘 따른다
   ↓
Agent 실행 (workflow: step 1..N)
   ↓  각 step: prompt(registry) + context → LLM(infrastructure) → 검증
   ↓
결과 조립 → 리포트/이벤트 발행
```

## 원칙
- **프롬프트는 registry/prompts 에서** 가져온다. 코드에 인라인 금지.
- **LLM 출력은 항상 검증**한다(스키마/파싱). 실패 시 재시도/폴백 경로.
- Agent step은 작고 관찰 가능해야 한다. 각 step의 입력/출력을 감사(`platform/audit`)에 남긴다.
- 벤더(OpenAI↔Anthropic) 교체가 Agent 로직에 영향 주지 않도록 인프라 인터페이스 뒤에 둔다.

## Playbook과의 관계
Playbook(`.ai/playbooks/`)은 "무엇을 어떤 순서로"를 사람이 읽는 형태로 정의하고,
workflow는 그 절차를 코드로 실행한다. 새 분석 유형 추가 = 새 Playbook + workflow 매핑.
