"""DIP API 진입점.

첫 커밋 범위: 앱 부트스트랩 + /health (Postgres 연결 확인 포함).
라우터/미들웨어/의존성은 apps/api/{routers,middlewares,dependencies} 로 점진 확장한다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.routers import ask, impact_analyses, incidents, issues
from apps.composition import build_and_run
from infrastructure.postgres import connection as pg
from shared.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup: 인메모리 파이프라인을 조립·실행해 리포트 데이터를 준비한다.
    app.state.dip = await build_and_run()
    yield
    # shutdown: 커넥션 풀 정리
    await pg.dispose()


app = FastAPI(
    title="Developer Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(issues.router)
app.include_router(impact_analyses.router)
app.include_router(incidents.router)
app.include_router(ask.router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, object]:
    settings = get_settings()
    db_ok = await pg.ping()
    return {
        "status": "ok" if db_ok else "degraded",
        "env": settings.app_env,
        "version": app.version,
        "dependencies": {"postgres": "up" if db_ok else "down"},
    }
