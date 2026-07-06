# Sprint-13 — Incident Library + 선택적 MSA 분리 검토

- 상태: Todo
- Phase / Milestone: Phase 4 (Product & Ops) / M4
- 의존성: **Sprint-10/11** (판단 결과·리포트 존재), Sprint-05 (Knowledge Library)
- 마지막 계획 Sprint(이후 운영·반복)

## 문제 (Discovery)
① 장애 지식을 **Incident Library**로 성숙시킨다(승격 2: Knowledge → Incident Library).
② Modular Monolith에서 **서비스로 분리할 모듈이 있는지** 판단한다(roadmap 분리 기준).

## 범위
- 하는 것:
  - **Promotion(승격 2)**: Knowledge → Incident Library(근본원인/해결/재발방지, **사실 근거 필수**)([../architecture/knowledge-lifecycle.md]).
  - `database/migrations/005_incidents.sql` 또는 Knowledge 확장.
  - Incident 템플릿([../templates/incident.md]) 기반 산출.
  - **MSA 분리 검토 보고서**: 트래픽/배포주기/팀경계 기준으로 후보 모듈 평가 → 분리/유지 결정을 ADR 초안으로.
- 안 하는 것(Non-goals):
  - 실제 서비스 분리 실행(승인 후 별도 Sprint), 자동 장애 감지 전면.

## 성공 기준 (DoD)
- [ ] Knowledge로부터 Incident 지식이 **출처를 보존**하며 승격된다(불변식 준수).
- [ ] Incident 승격 시 근본원인이 사실 근거(Event/Knowledge)에 연결된다.
- [ ] 분리 후보 모듈에 대한 판단 보고서 + 필요 시 ADR 초안 산출.
- [ ] ruff/mypy/pytest 통과.

## 설계 메모 (Design)
- 승격은 append(파괴 금지), LLM 사용 시 스키마 검증([../contracts/knowledge-contract.md]).
- 분리는 "폴더를 통째로 떼도 실행되는가" 기준을 실측으로 확인([../contracts/module-contract.md]).

## Approval Gate — 착수 전/판단 시
- **[APR-008]** MSA 분리 결정(어떤 모듈을 언제 분리) (Pending).

## 체크리스트
- [ ] 구현 (incident 승격 → library)
- [ ] 분리 검토 보고서/ADR 초안
- [ ] 리뷰 · Phase 4 반영
- [ ] `roadmap`/`milestones`/`state` 갱신

## 회고
- 잘된 것:
- 개선할 것:
