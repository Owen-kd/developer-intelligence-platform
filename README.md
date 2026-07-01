# DIP — Developer Intelligence Platform

Jira · Git · Codebase · Incident 데이터를 하나의 **AI Context**로 엮어
이슈 분류(Triage), 영향도 분석(Impact), 코드 리뷰, 릴리즈 판단을 자동화하는 플랫폼.

> 처음부터 MSA로 가지 않는다. 하지만 **언제든 서비스로 분리 가능한 Modular Monolith**로 설계한다.

## 아키텍처 한눈에

```
apps/            실행 진입점 (api / worker / scheduler / cli)
modules/         비즈니스 모듈 — 각 모듈은 DDD-lite(application/domain/infrastructure/presentation)
platform/        플랫폼 코어 (event / workflow / registry / auth / audit / context)
infrastructure/  외부 시스템 연동 (jira / git / openai / anthropic / neo4j / postgres / redis)
shared/          공통 (config / logger / exceptions / constants / utils / models)
database/        migrations / seed / schema
prompts/         코드 밖의 프롬프트 자산
.ai/             AI 개발 컨텍스트 (Claude / GPT / Codex / Cursor 공용 헌법)
```

**핵심 규칙**
- `modules/` 안에서 OpenAI/Anthropic 등 외부 API를 **직접 호출하지 않는다.** 항상 `infrastructure/`를 경유한다.
- 모듈 간 통신은 `platform/event`(EventBus)를 통한다. 모듈은 서로를 직접 import 하지 않는 방향을 지향한다.
- 프롬프트는 코드가 아니라 자산이다 (`prompts/`, `.ai/prompts/`).

전체 원칙은 [.ai/core/architecture-principles.md](.ai/core/architecture-principles.md) 참고.

## 빠른 시작

```bash
# 1) 인프라 기동 (Postgres / Neo4j / Redis)
docker compose up -d

# 2) 의존성 설치
pip install -e ".[dev]"

# 3) 환경변수
cp .env.example .env

# 4) API 실행
uvicorn apps.api.main:app --reload

# 5) 헬스체크
curl http://localhost:8000/health
```

## 문서

- AI 개발 프로세스: [.ai/workflow/](.ai/workflow/) (Discovery → Design → Implementation → Review → Release)
- 폴더 구조 상세: [.ai/architecture/folder-structure.md](.ai/architecture/folder-structure.md)
- 의사결정 기록(ADR): [.ai/decisions/](.ai/decisions/)
- 로드맵: [.ai/planning/roadmap.md](.ai/planning/roadmap.md)
