# Sprint-10 — Impact Agent

- 상태: Todo
- Phase / Milestone: Phase 3 (Agents) / M3
- 의존성: **Sprint-09**(Agent 골격), **Sprint-07**(그래프 — 영향 경로 탐색)
- 다음: Sprint-11 (Report API)

## 문제 (Discovery)
이슈/변경의 코드·API·DB **영향도**를 산출한다([../playbooks/impact-analysis.md]). 그래프(Neo4j) 관계를 근거로 Context를 조립해 Agent가 판단.

## 범위
- 하는 것:
  - `prompts/impact/analyze.md`.
  - Impact 플레이북 → workflow 매핑(Context는 Knowledge + 그래프 관계 근거 포함).
  - 결과 `impact_reports` 저장 + `ImpactAnalyzed` 발행 → Knowledge 축적.
  - `database/migrations/004_impact_reports.sql`.
- 안 하는 것(Non-goals):
  - Review/Release Agent(후속 Phase), 리포트 표현(→ Sprint-11).

## 성공 기준 (DoD)
- [ ] 이슈 1건에 대해 영향도 초안(요약+구조화 payload)이 생성·저장된다(roadmap Phase 3 Exit).
- [ ] 영향 근거가 그래프/Knowledge **출처**로 추적된다.
- [ ] LLM 출력 검증 통과분만 저장. Context Before AI. audit 기록.
- [ ] ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 그래프 관계(`TOUCHES`/`DEPENDS_ON`/`FIXES`)를 Context 근거로 사용.
- 원천 직접 소비 금지, LLM은 infrastructure 경유.

## Approval Gate
- 상위 [APR-005] 유효. 신규 Gate 없음.

## 체크리스트
- [ ] 구현 (migration → prompt → agent → report)
- [ ] 테스트
- [ ] 리뷰 · Phase 3 Exit 확인
- [ ] `milestones`(M3)/`state`/`roadmap` 갱신

## 회고
- 잘된 것:
- 개선할 것:
