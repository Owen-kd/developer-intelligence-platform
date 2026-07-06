# Current Task

> AI가 세션 시작 시 "지금 무엇을 하는 중인가"를 파악하는 파일. 작업이 바뀌면 갱신한다.

## 현재 스프린트
**완주 완료** — Sprint-02~13(Phase 1~4) 전 파이프라인 구현·검증 완료 (2026-07-07).
수집→그래프→Knowledge→Context→Triage/Impact Agent→Report API→Incident Library 가 end-to-end 로 동작한다.
품질 게이트 통과(ruff / mypy strict 170 files / pytest 39) + 라이브 Postgres 스모크 통과.
상세 현황: [../state/current-architecture.md](../state/current-architecture.md) · 리뷰: [../reviews/review-001.md](../reviews/review-001.md).
이전: [Sprint-01](../tasks/Sprint-01.md) 골격, Sprint 0 문서 정비 완료.

## 진행 중 (Sprint 0)
- [x] `.ai` 확장: contracts / philosophy / glossary / standards / planning / state / onboarding / references
- [x] roadmap 을 `context/` → `planning/` 으로 이동, 참조 갱신
- [x] architecture 강화: context-engine / knowledge-lifecycle
- [x] prompts 디렉터리 추가: `prompts/knowledge`, `prompts/incident`
- [x] `.ai/README.md` 인덱스 개정

## 다음 후보 (M1 — First Collector, 코드 재개 시)
- [ ] EventBus 인터페이스 (`platform/event`) → [Sprint-02](../tasks/Sprint-02.md)
- [ ] 첫 도메인 모듈: `jira` (Collector → Event → 저장) → [Sprint-03](../tasks/Sprint-03.md)
- [ ] Jira 동기화 스케줄러 (`apps/scheduler/jira_sync.py`) → Sprint-03
- [ ] Context Builder (`platform/context`) → [Sprint-06](../tasks/Sprint-06.md)
- 상세: [../planning/milestones.md](../planning/milestones.md) · [../planning/backlog.md](../planning/backlog.md)

## 완주 계획 (Project Planner 산출, 2026-07-07)
- 전체 Sprint 지도 + 의존성 그래프 + Approval Gate: **[../planning/sprint-plan.md](../planning/sprint-plan.md)**
- 사람 승인 대기(착수 전 필요): **[../planning/approvals/](../planning/approvals/)** — APR-001~009, 모두 Pending.
- 크리티컬 패스: Sprint-02 → 03 → 05 → 06 → 08 → 09 → 10 → 11 → 13.
- 주의: 코드 착수는 여전히 "현재 Sprint만". 계획 문서는 미래 구현 승인이 아니다.

## 제안된 결정 (승인 대기)
- ADR-004(제안): "AI는 Knowledge만 소비한다"를 불변 규칙으로 승격 — [APR-001](../planning/approvals/APR-001-adr004-knowledge-only.md) · [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md) 하단 참조.

## 메모
- 로컬 Python은 시스템 3.9 → 3.11+ 필요. venv는 Homebrew python3.14로 생성됨.
