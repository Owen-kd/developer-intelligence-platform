# APR-006 — `platform/audit` 조기 도입 (마일스톤 순서 이탈)

- 상태: Pending Approval
- 요청일: 2026-07-07
- 요청자: Project Planner (AI)
- 관련 Sprint: Sprint-08 (최소 도입), Sprint-12 (완성)

## 요청 요약
현재 계획상 `platform/audit`는 Phase 4(Sprint-12)다. 그러나 **event-flow / agent-flow 설계는 이미 audit을 전제**한다(실패 핸들러 로깅, 각 Agent step 감사). Phase 3(Sprint-08)에서 **최소 audit**을 조기 도입하도록 승인을 요청한다.

## 왜 사람이 결정해야 하나
- 마일스톤 순서를 바꾸는 설계 판단이다(Planner가 임의로 순서를 흔들지 않는다).
- system.md: 확인 없이 아키텍처/계획 변경 금지.

## 근거 (충돌 지점)
- [event-flow.md]: "실패한 핸들러는 … 감사 로그(`platform/audit`)".
- [agent-flow.md]/[agent-contract.md]: "각 step의 입력/출력을 감사(`platform/audit`)에 남긴다".
→ Agent(Sprint-09~10)를 audit 없이 만들면 계약 위반 또는 후속 재작업.

## 선택지
1. **(추천)** Sprint-08에서 **최소 audit**(구조화 로깅+기록 인터페이스)만 도입, Sprint-12에서 정식 완성.
2. 순서 유지 — Agent 단계에선 임시 로깅만, audit은 Phase 4.
3. audit 전체를 Phase 3로 당김(범위 증가).

## 영향
- 승인 시: Sprint-08 범위에 audit 최소본 포함(이미 Sprint-08 문서에 반영됨), 계약 위반 없음.
- 미승인 시: Sprint-08/09/10 문서에서 audit 항목 제거 + 임시 로깅 주석 명시 필요.

## 승인 체크
- [ ] 승인 (최소 도입)
- [ ] 조건부 승인 (조건: __________)
- [ ] 거부 (순서 유지)
