# Philosophy — Event Driven

> 왜 DIP는 상태를 덮어쓰지 않고 Event로 기록하는가.

## 핵심 명제
**중요한 것은 모두 Event가 된다. 프로젝트의 역사는 절대 덮어쓰지 않는다.**

## 문제 인식
전통적인 CRUD는 "현재 상태"만 남긴다.
- 이슈 상태를 `In Progress → Done` 으로 바꾸면 그 사이의 판단·논의·맥락이 사라진다.
- 장애가 어떻게 전개됐는지의 **시간 축**이 남지 않는다.
- 지식은 "결과"가 아니라 "과정"에서 나오는데, 과정이 지워진다.

## 우리의 선택
1. **Append-only.** 상태를 덮어쓰는 대신 무슨 일이 있었는지를 Event로 추가한다.
2. Event들이 모여 **Timeline** 을 이룬다(이슈/장애 단위의 시간 축).
3. Timeline 으로부터 **Knowledge** 가 생성(승격, Promotion)된다.
4. Knowledge 로부터 **Incident Library** 의 지식이 생성된다.

```
Issue → Timeline → Knowledge → Incident Library
      (Events)   (Promotion)  (Promotion)
```

## 모듈 통신에도 같은 철학
- 모듈은 서로를 직접 호출하지 않고, Event를 발행/구독한다([../architecture/event-flow.md]).
- 하나의 사실(예: 이슈 인입)이 여러 반응(수집·조립·분석)을 유발하는 팬아웃이 자연스럽다.
- 결합도가 낮아져 각 모듈을 독립적으로 발전·분리시킬 수 있다.

## 왜 이렇게 하는가
- **역사 보존**: 판단의 근거가 사라지지 않는다 → 지식의 출처 추적 가능.
- **재현성**: Timeline을 재생하면 "그때 무슨 일이 있었나"를 복원할 수 있다.
- **지식 생성의 원천**: Knowledge는 Event로부터 파생된다. Event가 없으면 정제할 원료가 없다.
- **멱등·복원력**: Event 소비자는 멱등적으로 설계되어 재처리·복구가 안전하다.

## 규칙
- 중요한 변화는 상태 갱신이 아니라 Event 발행으로 표현한다.
- Event는 불변(immutable)이며 과거형 이름을 가진다(`IssueCreated`).
- Event 소비 핸들러는 멱등이어야 한다.

## 관련 문서
- [knowledge-first.md](knowledge-first.md) · [context-over-prompt.md](context-over-prompt.md)
- [../contracts/event-contract.md](../contracts/event-contract.md)
- [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md)
