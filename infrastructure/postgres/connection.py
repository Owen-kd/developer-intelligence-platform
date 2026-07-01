"""Postgres 연결 (SQLAlchemy 2.0 async).

외부 시스템 연동은 반드시 이 infrastructure 계층을 경유한다.
modules/ 는 여기서 노출하는 session/health API만 사용한다.
"""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from shared.config.settings import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.postgres_dsn,
            echo=settings.app_debug,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency 로 주입되는 세션."""
    async with get_session_factory()() as session:
        yield session


async def ping() -> bool:
    """헬스체크용 연결 확인. 실패해도 예외를 삼키고 False 반환."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def dispose() -> None:
    """앱 종료 시 커넥션 풀 정리."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
