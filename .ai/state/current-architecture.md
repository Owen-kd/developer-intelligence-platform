# State — Current Architecture

> **지금 실제로 구현된 것**만 기록한다(설계 의도가 아니라 현실). 이정표 완료 시 갱신한다.
> 목표 구조: [../architecture/](../architecture/) · 로드맵: [../planning/roadmap.md](../planning/roadmap.md)

_기준: Phase 0 (Foundation) 진행 중 / Sprint 0 — AI Operating System 정비_

## 실제로 존재하는 것
- **저장소 골격**: `apps/ modules/ platform/ infrastructure/ shared/` + `database/ prompts/ tests/ docker/` 폴더 골격(대부분 `__init__.py`/`.gitkeep` 뼈대).
- **실행 코드(동작 확인됨)**:
  - `apps/api/main.py` — FastAPI + `/health`(Postgres ping, DB 다운 시 200/degraded)
  - `shared/config/settings.py` — pydantic-settings 중앙 설정
  - `infrastructure/postgres/connection.py` — SQLAlchemy 2.0 async 연결 + `ping()`
  - `tests/unit/test_health.py` — 스모크 테스트(통과)
- **인프라**: `docker-compose.yml`(postgres/neo4j/redis) 정의.
- **품질 게이트**: ruff / mypy(strict) / pytest 통과 확인됨.
- **AI Operating System**: `.ai/`(core/context/architecture/workflow/playbooks/decisions/contracts/philosophy/glossary/standards/planning/state/onboarding/references/templates).

## 아직 코드가 없는 것 (문서·골격만)
- `platform/event`(EventBus) — 인터페이스/구현 없음(설계·계약만 존재).
- `platform/context`(Context Builder) — 설계만.
- `platform/workflow` / registry / auth / audit — 골격만.
- 모든 `modules/*`(jira/comment/incident/git/code/...) — DDD 폴더 골격만, 로직 없음.
- Collector / Knowledge / Timeline / Incident Library — 파이프라인 미구현.
- `infrastructure/{jira,git,openai,anthropic,neo4j,redis}` — 골격만(postgres만 구현).
- `database/migrations` — 비어 있음(스키마 미적용).

## 진입점 현황
- `api`: 동작(`uvicorn apps.api.main:app`).
- `worker` / `scheduler` / `cli`: 골격만.

## 요약
현재는 **"실행 가능한 뼈대 + AI 운영체계"** 단계다. 비즈니스 파이프라인(수집→지식→컨텍스트→에이전트)은 아직 구현되지 않았다.
다음: [../planning/milestones.md](../planning/milestones.md) M1(First Collector).
