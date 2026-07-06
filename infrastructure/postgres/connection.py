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


def _split_statements(sql: str) -> list[str]:
    """SQL 스크립트를 개별 문장으로 분리한다(라인 주석 제거 후 세미콜론 기준).

    asyncpg 는 prepared statement 에 다중 문장을 허용하지 않으므로 문장 단위로 실행한다.
    (마이그레이션 DDL 은 문자열 리터럴 안에 `--`/`;` 를 두지 않는다는 전제.)
    """
    without_comments = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [stmt.strip() for stmt in without_comments.split(";") if stmt.strip()]


async def run_script(sql: str) -> None:
    """다중 문장 SQL 스크립트를 하나의 트랜잭션으로 실행한다(마이그레이션용)."""
    async with get_engine().begin() as conn:
        for statement in _split_statements(sql):
            await conn.exec_driver_sql(statement)


async def dispose() -> None:
    """앱 종료 시 커넥션 풀 정리."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
