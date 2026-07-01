# Philosophy — Context over Prompt

> 왜 DIP는 "좋은 프롬프트"가 아니라 "좋은 Context"에 투자하는가.

## 핵심 명제
**AI의 출력 품질은 프롬프트 기교가 아니라 입력된 Context의 품질이 결정한다.**
그래서 우리는 프롬프트 튜닝보다 **Context Builder** 에 투자한다.

## 문제 인식
- 프롬프트만 정교하게 다듬어도, 원천 데이터가 노이즈면 결과는 나빠진다.
- 원천 데이터를 통째로 넣으면 토큰이 폭발하고 핵심이 묻힌다.
- 프롬프트를 코드에 하드코딩하면 자산으로 관리·재사용되지 않는다.

## 우리의 선택
1. **Context Before AI.** LLM 호출 전에 항상 Context Builder가 Context를 조립한다.
2. Context는 원천 데이터가 아니라 **Knowledge** 를 기반으로 조립된다([knowledge-first.md]).
3. **프롬프트는 코드가 아니라 자산**이다 → `prompts/`, `.ai/prompts/` 에 둔다.
4. AI는 파이프라인의 **마지막** 단계다. AI Last.

```
Knowledge → Context Builder → Context → (prompt 자산) → Agent/LLM → 결과
```

## 왜 이렇게 하는가
- **품질**: 정제된 Knowledge 기반 Context는 신호가 강하다.
- **비용**: 필요한 것만 넣으므로 토큰이 절약된다.
- **일관성**: 같은 Context 조립 규칙 → 재현 가능한 결과.
- **교체 용이**: 프롬프트가 자산이면 모델·벤더 교체 시 Context/프롬프트를 독립적으로 조정할 수 있다.

## 규칙
- 어떤 모듈도 원천 데이터를 LLM에 직접 보내지 않는다.
- LLM 호출은 반드시 Context Builder가 준비한 Context를 사용한다.
- 프롬프트 문자열을 코드에 인라인하지 않는다.
- 외부 LLM 호출은 `infrastructure/{openai,anthropic}` 를 경유한다.

## 관련 문서
- [../architecture/context-engine.md](../architecture/context-engine.md) — Context Builder 설계
- [../architecture/agent-flow.md](../architecture/agent-flow.md) — Agent 실행 파이프라인
- [../contracts/agent-contract.md](../contracts/agent-contract.md)
