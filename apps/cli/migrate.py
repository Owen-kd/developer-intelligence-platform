"""마이그레이션 적용 CLI (최소 경로).

`database/migrations/NNN_*.sql` 을 파일명 순서대로 실행한다.
앱은 임의 DDL 을 하지 않는다 — 스키마 변경은 오직 이 경로로만.

사용:
    python -m apps.cli.migrate
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from infrastructure.postgres import connection as pg
from shared.logger import get_logger

_logger = get_logger("cli.migrate")

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "database" / "migrations"


def discover_migrations(migrations_dir: Path) -> list[Path]:
    """`*.sql` 마이그레이션을 파일명 오름차순으로 반환한다(순수 함수).

    파일명 규약 `NNN_설명.sql` 을 사전순 정렬하면 곧 적용 순서가 된다.
    """
    return sorted(migrations_dir.glob("*.sql"), key=lambda path: path.name)


async def apply_migrations(migrations_dir: Path | None = None) -> list[str]:
    """마이그레이션을 순서대로 적용하고 적용된 파일명을 반환한다."""
    target = migrations_dir or _MIGRATIONS_DIR
    applied: list[str] = []
    for migration in discover_migrations(target):
        sql = migration.read_text(encoding="utf-8")
        await pg.run_script(sql)
        _logger.info("migration.applied", file=migration.name)
        applied.append(migration.name)
    return applied


async def _main() -> None:
    try:
        applied = await apply_migrations()
        _logger.info("migration.done", count=len(applied))
    finally:
        await pg.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
