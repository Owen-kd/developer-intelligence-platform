# Sprint-05 — Knowledge 승격 파이프라인

- 상태: Todo
- Phase / Milestone: Phase 2 (Knowledge & Context) / M2
- 의존성: **Sprint-03/04** (Event/Timeline 원천 존재)
- 다음: Sprint-06 (Context Builder), Sprint-07 (임베딩/그래프) — 병렬

## 문제 (Discovery)
DIP의 존재 이유는 원천 데이터를 **재사용 가능한 Knowledge**로 승격하는 것이다([../philosophy/knowledge-first.md]).
지금은 Event만 쌓이고 정제 계층이 없다.

## 범위
- 하는 것:
  - **Timeline** 조회: 엔티티(issue)별 Event 시간축 구성(덮어쓰기 금지).
  - **Promotion(승격 1)**: Event/Timeline → `Knowledge`(요약+구조화 본문+**출처(Event 참조)**+생성시각).
  - `database/migrations/003_knowledge.sql`: `knowledge` 저장소(출처 배열 포함).
  - Knowledge Library 저장/조회 인터페이스.
  - LLM 사용 시 **스키마 검증 후 저장**(이 Sprint는 규칙 기반 우선, LLM 승격은 선택).
- 안 하는 것(Non-goals):
  - Incident Library(승격 2 → Sprint-13), Context 조립(→ Sprint-06), 임베딩(→ Sprint-07).

## 성공 기준 (DoD)
- [ ] 이슈 1건의 Event/Timeline으로부터 최소 1개 Knowledge가 생성되고 **출처(Event id)** 를 보존한다.
- [ ] Promotion은 파괴가 아니라 **append**(기존 Event/Knowledge 불변) — 불변식 검증.
- [ ] (LLM 사용 시) 스키마 검증 실패한 출력은 저장되지 않는다.
- [ ] ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 불변식 준수([../architecture/knowledge-lifecycle.md]): Event 불변 / 모든 Knowledge는 출처 보유 / 검증 후 저장 / append.
- 계약: [../contracts/knowledge-contract.md]. 프롬프트 사용 시 `prompts/knowledge/`(코드 인라인 금지).
- 배치: 승격 오케스트레이션의 소유 위치를 Design에서 확정(모듈 vs platform) — 모듈 경계 유지.

## Approval Gate — 착수 전
- **[APR-001]** ADR-004 "AI는 Knowledge만 소비" 불변 규칙 승격 (Pending) — 이후 Agent 단계의 전제.

## 체크리스트
- [ ] 구현 (timeline → promotion → knowledge store)
- [ ] 불변식 테스트
- [ ] 리뷰 · ADR-004 확정 반영
- [ ] `state`/`milestones`(M2) 갱신

## 회고
- 잘된 것:
- 개선할 것:
