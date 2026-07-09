"""스케줄러 수집(run_once) 단위 테스트 — Jira 수집 → IssueCreated 발행(주입 어댑터)."""

from __future__ import annotations

from apps.scheduler.run import run_once
from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from infrastructure.jira.client import FakeJiraClient
from modules.jira.domain.events import ISSUE_CREATED
from modules.jira.infrastructure.repository import InMemoryIssueRepository


async def test_run_once_collects_and_publishes_events() -> None:
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)

    result = await run_once(
        bus, jira_client=FakeJiraClient(), issue_repo=InMemoryIssueRepository()
    )

    assert result.issues_created >= 1
    assert any(event.name == ISSUE_CREATED for event in store.events)
