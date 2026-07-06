# Sprint-09 — Triage Agent

- 상태: Todo
- Phase / Milestone: Phase 3 (Agents) / M3
- 의존성: **Sprint-08** (LLM 인프라 + registry + workflow + audit)
- 다음: Sprint-10 (Impact Agent)

## 문제 (Discovery)
M3의 첫 Agent: 새 이슈를 **자동 분류/우선순위화**하고 결과를 Knowledge로 축적한다([../playbooks/jira-analysis.md]).

## 범위
- 하는 것:
  - `prompts/triage/classify.md`(프롬프트 자산).
  - Triage Agent(workflow step): `Context → prompt → LLM → 검증 → { category, priority, rationale, confidence }`.
  - 결과 `IssueTriaged` 발행 → Knowledge 승격 경로 연결.
  - 트리거: `ContextAssembled`(이벤트) 또는 API/CLI 수동 트리거.
- 안 하는 것(Non-goals):
  - Impact 분석(→ Sprint-10), 리포트 UI(→ Sprint-11).

## 성공 기준 (DoD)
- [ ] 새 이슈 → 자동 분류 결과가 생성되고 **Knowledge로 축적**된다(M3 DoD).
- [ ] LLM 출력이 스키마 검증을 통과해야만 Event/Knowledge가 된다(실패 시 재시도/폴백).
- [ ] Context 없이는 LLM을 호출하지 않는다(Context Before AI).
- [ ] step 입출력 audit 기록. unit은 LLM 목킹. ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- Agent는 Context 범위 안에서만 추론, 원천 데이터 직접 소비 금지([../contracts/agent-contract.md]).
- Playbook([../playbooks/jira-analysis.md])을 workflow로 매핑.

## Approval Gate
- 상위 [APR-005](데이터 정책) 유효. 신규 Gate 없음.

## 체크리스트
- [ ] 구현 (prompt → agent step → 검증 → event)
- [ ] 테스트(검증/폴백/멱등)
- [ ] 리뷰 · M3 DoD 확인
- [ ] `milestones`(M3)/`state` 갱신

## 회고
- 잘된 것:
- 개선할 것:
