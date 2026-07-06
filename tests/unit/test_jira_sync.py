"""Jira Collector 단위 테스트 — 적재/발행/멱등(인메모리 어댑터)."""

from __future__ import annotations

from apps.scheduler.jira_sync import build_in_memory_service, run_once
from dip_platform.event import InMemoryEventBus
from infrastructure.jira.client import FakeJiraClient
from modules.jira.application.service import JiraService
from modules.jira.domain.events import COMMENT_ADDED, ISSUE_CREATED
from modules.jira.infrastructure.repository import InMemoryIssueRepository


async def test_sync_persists_and_publishes() -> None:
    service, store = build_in_memory_service()

    result = await run_once(service)

    assert result.issues_synced == 1
    assert result.issues_created == 1
    assert result.comments_added == 2

    names = [event.name for event in store.events]
    assert names.count(ISSUE_CREATED) == 1
    assert names.count(COMMENT_ADDED) == 2


async def test_sync_is_idempotent() -> None:
    service, store = build_in_memory_service()

    await run_once(service)
    events_after_first = len(store.events)

    second = await run_once(service)

    assert second.issues_created == 0
    assert second.comments_added == 0
    # 재실행은 새 이벤트를 만들지 않는다(멱등).
    assert len(store.events) == events_after_first


async def test_repo_stores_issue_with_comments() -> None:
    repo = InMemoryIssueRepository()
    service = JiraService(FakeJiraClient(), repo, InMemoryEventBus())

    await service.sync()

    issue = await repo.get_issue("DIP-1")
    assert issue is not None
    assert issue.id is not None
    assert len(issue.comments) == 2
