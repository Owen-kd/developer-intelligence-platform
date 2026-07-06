"""실 Jira 수집 → Postgres 적재 (실데이터 경로).

fixture 가 아니라 실 Jira(.env 설정)에서 이슈/코멘트를 수집해 Postgres 에 영속화한다.
같은 포트를 쓰므로 서비스/도메인 코드는 fake 경로와 동일하다.

사용:
    python -m apps.cli.collect_jira [최대이슈수]
"""

from __future__ import annotations

import asyncio
import sys

from apps.cli.migrate import apply_migrations
from dip_platform.event import InMemoryEventBus
from infrastructure.jira.client import http_client_from_settings
from infrastructure.postgres import connection as pg
from infrastructure.postgres.event_store import PostgresEventStore
from modules.jira.application.service import JiraService
from modules.jira.infrastructure.repository import PostgresIssueRepository
from shared.logger import get_logger

_logger = get_logger("cli.collect_jira")


async def collect(limit: int) -> None:
    await apply_migrations()  # 스키마 보장(멱등)
    bus = InMemoryEventBus(store=PostgresEventStore())
    service = JiraService(
        client=http_client_from_settings(limit=limit),
        repo=PostgresIssueRepository(),
        bus=bus,
    )
    try:
        result = await service.sync()
        _logger.info(
            "collect_jira.done",
            issues_synced=result.issues_synced,
            issues_created=result.issues_created,
            comments_added=result.comments_added,
        )
    finally:
        await pg.dispose()


async def _main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    await collect(limit)


if __name__ == "__main__":
    asyncio.run(_main())
