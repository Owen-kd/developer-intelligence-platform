# Current Task

> AI가 세션 시작 시 "지금 무엇을 하는 중인가"를 파악하는 파일. 작업이 바뀌면 갱신한다.

## 현재 스프린트
**Sprint 0 — AI Operating System 정비** (문서 전용, 코드 변경 없음).
이전: [Sprint-01](../tasks/Sprint-01.md) 스캐폴딩 & 골격 완료.

## 진행 중 (Sprint 0)
- [x] `.ai` 확장: contracts / philosophy / glossary / standards / planning / state / onboarding / references
- [x] roadmap 을 `context/` → `planning/` 으로 이동, 참조 갱신
- [x] architecture 강화: context-engine / knowledge-lifecycle
- [x] prompts 디렉터리 추가: `prompts/knowledge`, `prompts/incident`
- [x] `.ai/README.md` 인덱스 개정

## 다음 후보 (M1 — First Collector, 코드 재개 시)
- [ ] EventBus 인터페이스 (`platform/event`)
- [ ] 첫 도메인 모듈: `jira` (Collector → Event → 저장)
- [ ] Jira 동기화 스케줄러 (`apps/scheduler/jira_sync.py`)
- [ ] Context Builder (`platform/context`)
- 상세: [../planning/milestones.md](../planning/milestones.md) · [../planning/backlog.md](../planning/backlog.md)

## 제안된 결정 (승인 대기)
- ADR-004(제안): "AI는 Knowledge만 소비한다"를 불변 규칙으로 승격 — [../architecture/knowledge-lifecycle.md](../architecture/knowledge-lifecycle.md) 하단 참조.

## 메모
- 로컬 Python은 시스템 3.9 → 3.11+ 필요. venv는 Homebrew python3.14로 생성됨.
