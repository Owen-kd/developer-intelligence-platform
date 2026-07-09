"""상시 Scheduler — 주기 Jira 수집 → Redis 로 이벤트 발행(LLM 0). target-service 루프1.

수집만 한다(스크러빙은 수집 어댑터가 담당). 발행된 IssueCreated 를 worker 가 받아 지식화한다.

⚠️ 게이트: 실 Jira 대량 자동수집은 APR-002 승인 사안(.ai/planning/approvals/APR-002).
기본 비활성(`SCHEDULER_ENABLED=false`) — 오발 방지. 승인 후 `SCHEDULER_ENABLED=true` 로 켠다.

실행:
    python -m apps.scheduler.run
"""

from __future__ import annotations

import asyncio

from apps.wiki_pipeline import _build_jira_client
from dip_platform.event import EventBus
from infrastructure.postgres import connection as pg
from infrastructure.postgres.event_store import PostgresEventStore
from infrastructure.redis.event_bus import RedisEventBus
from modules.jira.application.service import JiraService, SyncResult
from modules.jira.domain.repository import IssueRepository
from modules.jira.infrastructure.repository import PostgresIssueRepository
from shared.config.settings import get_settings
from shared.logger import get_logger

_logger = get_logger("apps.scheduler")


async def run_once(
    bus: EventBus,
    *,
    jira_client: object | None = None,
    issue_repo: IssueRepository | None = None,
) -> SyncResult:
    """1회 Jira 수집 → 신규 이슈 IssueCreated 발행. (테스트는 어댑터를 주입)."""
    settings = get_settings()
    repo = issue_repo or PostgresIssueRepository()
    client = jira_client or _build_jira_client(settings)[0]
    return await JiraService(client, repo, bus).sync()  # type: ignore[arg-type]


async def _main() -> None:
    settings = get_settings()
    if not settings.scheduler_enabled:
        _logger.warning(
            "scheduler.disabled",
            hint="SCHEDULER_ENABLED=true (APR-002 승인 후) 로 활성화",
        )
        return

    bus = RedisEventBus(settings.redis_url, store=PostgresEventStore())
    _logger.info("scheduler.starting", interval_s=settings.scheduler_interval_seconds)
    try:
        while True:
            result = await run_once(bus)
            _logger.info(
                "scheduler.synced",
                issues=result.issues_synced,
                created=result.issues_created,
            )
            await asyncio.sleep(settings.scheduler_interval_seconds)
    finally:
        await bus.aclose()
        await pg.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
