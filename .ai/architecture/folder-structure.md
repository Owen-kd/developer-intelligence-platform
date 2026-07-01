# Folder Structure

```
developer-intelligence-platform/
├── .ai/                    # AI 개발 컨텍스트 (헌법/컨텍스트/플레이북/워크플로우)
├── apps/                   # 실행 진입점
│   ├── api/                #   FastAPI (main.py, routers/, middlewares/, dependencies/)
│   ├── worker/             #   비동기 (embedding/, graph/, agent/)
│   ├── scheduler/          #   주기 동기화 (jira_sync/git_sync/comment_sync)
│   └── cli/
├── modules/                # 비즈니스 모듈 — 각자 DDD-lite
│   ├── jira/  comment/  incident/  git/  code/
│   ├── database/  embedding/  search/  graph/  llm/
│   └── <module>/
│       ├── application/    #   service.py (유스케이스)
│       ├── domain/         #   entity.py, repository.py(추상)
│       ├── infrastructure/ #   client.py, repository 구현
│       └── presentation/   #   controller.py, dto.py
├── platform/               # 플랫폼 코어
│   ├── event/   workflow/  registry/
│   └── auth/    audit/     context/
├── infrastructure/         # 외부 연동 (어댑터)
│   ├── jira/  git/  openai/  anthropic/
│   └── neo4j/ postgres/ redis/
├── shared/                 # 공통 (config/logger/exceptions/constants/utils/models)
├── database/               # migrations/ seed/ schema/
├── prompts/                # 코드 밖 프롬프트 (triage/impact/comment/review)
├── scripts/  docs/  tests/(unit/integration/e2e)
├── docker/                 # postgres/ neo4j/ redis
├── pyproject.toml  docker-compose.yml  .env(.example)  README.md
```

## 규칙 요약
- **한 방향 의존**: `apps → modules → platform → infrastructure → shared`.
- **모듈 자율성**: 각 `modules/<x>` 는 통째로 서비스 분리 가능해야 한다.
- **외부 호출 격리**: 외부 API는 `infrastructure/` 에만.
- **Python 패키지**는 `__init__.py`, 그 외 자산 폴더는 `.gitkeep` 로 골격 유지.

세부 규칙: [../core/architecture-principles.md](../core/architecture-principles.md)
