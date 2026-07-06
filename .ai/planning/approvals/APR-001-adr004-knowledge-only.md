# APR-001 — ADR-004 "AI는 Knowledge만 소비" 불변 규칙 승격

- 상태: Pending Approval
- 요청일: 2026-07-07
- 요청자: Project Planner (AI)
- 관련 Sprint: Sprint-05 (전제), Sprint-08~10 (적용)
- 관련 ADR: ADR-004 (제안) · 근거: [../../architecture/knowledge-lifecycle.md]

## 요청 요약
"AI(Agent)는 **Knowledge만** 소비하고 원천 데이터를 직접 소비하지 않는다"를 프로젝트 **불변 규칙(ADR-004)** 으로 확정한다. 이미 [current-task]에 제안 상태로 대기 중이다.

## 왜 사람이 결정해야 하나
- 불변 규칙은 전 계층(Context Builder/Agent)의 설계를 구속한다. 되돌리기 비싸다.
- system.md 원칙: "근거 없이 규칙 승격/아키텍처 변경 금지 → 승인 필요".

## 선택지
1. **(추천) 승격** — ADR-004 Accepted. Context/Agent는 Knowledge만 입력.
2. 보류 — 설계 문서 수준 유지, 규칙화는 M2 후 재검토.
3. 완화 — 예외(원천 직접 조회) 허용 조건을 명시한 규칙.

## 영향
- 승인 시: Sprint-05/06/08~10이 이 규칙을 전제로 진행. contracts(agent/knowledge)와 일치.
- 거부/보류 시: Sprint-06(Context Builder) 입력 정의가 열린 채 진행 → 재작업 위험.

## 승인 체크
- [ ] 승인(ADR-004 Accepted)
- [ ] 조건부 승인 (조건: __________)
- [ ] 거부 / 보류
