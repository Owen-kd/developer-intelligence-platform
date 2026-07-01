"""DIP API 진입점.

첫 커밋 범위: 앱 부트스트랩 + /health (Postgres 연결 확인 포함).
라우터/미들웨어/의존성은 apps/api/{routers,middlewares,dependencies} 로 점진 확장한다.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.postgres import connection as pg
from shared.config.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup: 필요 시 이벤트버스/워커 초기화 지점
    yield
    # shutdown: 커넥션 풀 정리
    await pg.dispose()


app = FastAPI(
    title="Developer Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)


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
