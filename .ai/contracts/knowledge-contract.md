# Contract — Knowledge

> Knowledge가 지켜야 하는 계약. Knowledge는 AI가 소비하는 유일한 지식 자산이다.

## 목적
Event/Timeline을 **재사용 가능하고 출처 추적 가능한 지식**으로 정제(Promotion)한다.

## 책임
- 원천 데이터의 노이즈를 제거하고 신호(결정·원인·영향)를 남긴다.
- 어떤 Event로부터 생성됐는지 출처를 보존한다.
- Context Builder가 소비할 수 있는 일관된 형태를 유지한다.

## Input
- 하나 이상의 **Event** / **Timeline**.
- (Incident Library의 경우) 기존 **Knowledge**.

## Output
- **Knowledge** 항목: 요약 + 구조화된 본문 + 출처(Event 참조) + 생성 시각.
- Knowledge Library(또는 Incident Library)에 축적.

## Rules
- **AI는 Knowledge를 소비한다. 원천 데이터를 직접 소비하지 않는다.**
- Knowledge는 항상 출처(생성에 사용된 Event/Knowledge)를 명시한다.
- Promotion은 append 지향 — 기존 지식을 파괴하지 않고 새 버전/항목으로 축적한다.
- LLM으로 지식을 생성한 경우, 출력은 스키마 검증 후 저장한다.
- 승격 단계: `Event/Timeline → Knowledge`, `Knowledge → Incident Library`.

## Example
```
Knowledge {
  id: "kn_123",
  type: "root_cause",
  summary: "결제 타임아웃은 커넥션 풀 고갈에서 비롯",
  body: { ... 구조화 ... },
  sources: ["evt_a", "evt_b"],   # 출처 보존
  created_at: "2026-07-01T..."
}
```

## 관련
- [../philosophy/knowledge-first.md](../philosophy/knowledge-first.md) · [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md) · [../glossary/terms.md](../glossary/terms.md)
