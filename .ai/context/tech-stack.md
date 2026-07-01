# Tech Stack

| 영역 | 선택 | 비고 / ADR |
|------|------|-----------|
| 언어 | Python 3.11+ | [ADR-001](../decisions/ADR-001-python.md) |
| 웹 프레임워크 | FastAPI | [ADR-002](../decisions/ADR-002-fastapi.md) |
| ASGI 서버 | Uvicorn | |
| 검증/설정 | Pydantic v2 / pydantic-settings | |
| RDB | PostgreSQL 16 | 정형 데이터, 이슈/리포트 |
| ORM | SQLAlchemy 2.0 (async) | asyncpg 드라이버 |
| Graph DB | Neo4j 5 | 코드·이슈·의존성 그래프 |
| 캐시/큐 | Redis 7 | 캐시, 이벤트/작업 브로커 후보 |
| 내부 통신 | EventBus (자체) | [ADR-003](../decisions/ADR-003-eventbus.md) |
| LLM | OpenAI · Anthropic | infrastructure 계층에서만 호출 |
| 테스트 | pytest / pytest-asyncio / httpx | |
| 린트/포맷 | ruff | line-length 100 |
| 타입 | mypy (strict) | |
| 컨테이너 | Docker Compose | postgres/neo4j/redis |

## 실행 진입점 (apps/)
- `api` — FastAPI (`uvicorn apps.api.main:app`)
- `worker` — 비동기 작업 (embedding / graph / agent)
- `scheduler` — 주기 동기화 (jira / git / comment)
- `cli` — 운영/일회성 명령

## 버전 고정 원칙
- 런타임 의존성은 `pyproject.toml` 에 하한만 명시, lock은 후속 도입.
- 메이저 업그레이드는 ADR로 남긴다.
