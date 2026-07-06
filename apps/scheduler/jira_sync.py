"""Jira 주기 동기화 진입점.

기본은 fixture/인메모리 어댑터로 동작한다(외부 자격증명 불필요).
실제 Jira/Postgres 연동은 같은 포트를 만족하는 어댑터로 교체하면 된다([APR-002]).

사용:
    python -m apps.scheduler.jira_sync
"""

from __future__ import annotations

import asyncio

from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from infrastructure.jira.client import FakeJiraClient
from modules.jira.application.service import JiraService, SyncResult
from modules.jira.infrastructure.repository import InMemoryIssueRepository
from shared.logger import get_logger

_logger = get_logger("scheduler.jira_sync")


def build_in_memory_service() -> tuple[JiraService, InMemoryEventStore]:
    """fixture/인메모리 어댑터로 조립한 서비스와 이벤트 스토어를 반환한다."""
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)
    service = JiraService(
        client=FakeJiraClient(),
        repo=InMemoryIssueRepository(),
        bus=bus,
    )
    return service, store


async def run_once(service: JiraService) -> SyncResult:
    """1회 동기화."""
    return await service.sync()


async def _main() -> None:
    service, store = build_in_memory_service()
    result = await run_once(service)
    _logger.info(
        "jira_sync.finished",
        issues=result.issues_synced,
        created=result.issues_created,
        comments=result.comments_added,
        events=len(store.events),
    )


if __name__ == "__main__":
    asyncio.run(_main())
