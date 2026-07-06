# Sprint-11 — Report API

- 상태: Todo
- Phase / Milestone: Phase 4 (Product & Ops) / M4
- 의존성: **Sprint-09/10** (분류·영향도 결과 존재)
- 병렬 이후: Sprint-12, Sprint-13

## 문제 (Discovery)
축적된 판단(분류/영향도)을 사람이 조회할 수 있게 **리포트 API**로 노출한다(roadmap Phase 4).

## 범위
- 하는 것:
  - `apps/api/routers/issues.py`, `apps/api/routers/impact_analyses.py`(얇은 라우터 → service 위임).
  - 리소스 규약: 복수형 kebab(`/issues`, `/impact-analyses`), 통일 에러 형식, 201/422 매핑([../architecture/api-design.md]).
  - 조회 유스케이스: 이슈별 Knowledge/분류/영향도 리포트.
- 안 하는 것(Non-goals):
  - 프론트엔드 SPA(별도), 권한(→ Sprint-12), 쓰기/트리거 고도화.

## 성공 기준 (DoD)
- [ ] `/issues`, `/impact-analyses`로 축적 결과를 조회할 수 있다.
- [ ] 라우터는 외부 시스템 직접 호출 없음 → service → infrastructure.
- [ ] 에러 응답 형식 통일, httpx 기반 테스트 통과. ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 비즈니스 로직은 `modules/<x>/application/service.py`, 라우터는 얇게([../architecture/api-design.md]).
- 인증/감사는 다음 Sprint에서 일원화([../contracts/api-contract.md]).

## Approval Gate
- 없음(내부 노출). 외부 공개 시 [APR-005](데이터 노출) 재검토.

## 체크리스트
- [ ] 구현 (routers → service 위임 → dto)
- [ ] API 테스트
- [ ] 리뷰
- [ ] `state`/`roadmap`(Phase 4) 갱신

## 회고
- 잘된 것:
- 개선할 것:
