"""Git Collector 단위 테스트 — 파싱/링크/이벤트협업/멱등."""

from __future__ import annotations

from apps.scheduler.git_sync import build_in_memory_pipeline
from dip_platform.event import InMemoryEventBus
from infrastructure.git.client import FakeGitClient
from modules.git.application.service import GitService
from modules.git.domain.entity import parse_issue_keys
from modules.git.domain.events import COMMITS_LINKED
from modules.git.infrastructure.repository import InMemoryCommitRepository


def test_parse_issue_keys_dedup_and_order() -> None:
    keys = parse_issue_keys("DIP-1 관련 수정, 또 DIP-1 및 ABC-99 참조")
    assert keys == ["DIP-1", "ABC-99"]


async def test_git_links_commit_to_known_issue() -> None:
    jira, git, store = build_in_memory_pipeline()

    await jira.sync()  # git 이 DIP-1→issue_id 학습
    result = await git.sync()

    assert result.commits_synced == 2
    assert result.links_created == 1  # DIP-1 커밋 1건만 링크
    assert [event.name for event in store.events].count(COMMITS_LINKED) == 1


async def test_git_sync_is_idempotent() -> None:
    jira, git, store = build_in_memory_pipeline()
    await jira.sync()
    await git.sync()
    events_after_first = len(store.events)

    second = await git.sync()

    assert second.links_created == 0
    assert len(store.events) == events_after_first


async def test_no_link_when_issue_unknown() -> None:
    # jira.sync 를 돌리지 않아 매핑이 없으면 링크되지 않는다.
    git = GitService(FakeGitClient(), InMemoryCommitRepository(), InMemoryEventBus())

    result = await git.sync()

    assert result.commits_synced == 2
    assert result.links_created == 0
