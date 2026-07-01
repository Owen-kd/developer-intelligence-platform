# Philosophy — Knowledge First

> 왜 DIP는 "데이터"가 아니라 "지식(Knowledge)"을 중심에 두는가.

## 핵심 명제
**DIP는 회사의 운영 경험을 재사용 가능한 지식으로 축적하기 위해 존재한다.**
AI 챗봇을 만드는 것이 목적이 아니다.

## 문제 인식
운영 데이터(Jira 이슈, 코멘트, 커밋, 장애 로그)는 시간이 지나면 흩어지고 잊힌다.
- 같은 장애가 반복되지만, 지난번 해결 맥락은 사람 머릿속에만 있다.
- 이슈를 분류하고 영향도를 판단하는 "판단"이 매번 처음부터 다시 이뤄진다.
- 원천 데이터는 많지만, **재사용 가능한 형태로 정제된 지식**은 없다.

## 우리의 선택
1. **AI는 원천 데이터를 소비하지 않는다.** AI는 정제된 **Knowledge** 를 소비한다.
2. 원천 데이터 → Event → Timeline → **Knowledge** → **Incident Library** 로 승격(Promotion)된다.
3. 판단의 결과물(분류, 영향도, 근본 원인)도 다시 Knowledge 로 축적된다.
4. 지식이 쌓일수록 플랫폼은 더 똑똑해진다. 이것이 복리(compounding)다.

## 왜 이렇게 하는가
- **재사용성**: 한 번 정제한 지식은 다음 유사 상황에서 즉시 재사용된다.
- **품질**: 원천 데이터를 그대로 LLM에 넣으면 노이즈·토큰 낭비·환각이 늘어난다. 정제된 지식은 신호 대 잡음비가 높다.
- **감사 가능성**: 지식은 어떤 Event로부터 생성됐는지 추적 가능하다(출처 보존).
- **분리 가능성**: 지식 계층이 명확하면 수집·정제·소비를 독립적으로 발전·분리시킬 수 있다.

## 원칙으로서의 요약
> **Knowledge First. Context Before AI. AI Last.**

- 새 기능을 설계할 때 먼저 묻는다: "이건 어떤 Knowledge를 만들거나 소비하는가?"
- LLM 호출 전에 항상 Knowledge 기반 Context가 준비돼 있어야 한다.

## 관련 문서
- [event-driven.md](event-driven.md) — 지식이 어떻게 Event로부터 생성되는가
- [context-over-prompt.md](context-over-prompt.md) — 지식이 어떻게 Context로 조립되는가
- [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md) — 생명주기 구조
- [../glossary/terms.md](../glossary/terms.md) — 용어 정의
