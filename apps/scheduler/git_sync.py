"""Git 주기 동기화 진입점.

기본은 fixture/인메모리 어댑터. jira→git 협업(IssueCreated 구독)을 보이기 위해
jira 수집과 git 수집을 하나의 EventBus 로 조립한다.

사용:
    python -m apps.scheduler.git_sync
"""

from __future__ import annotations

import asyncio

from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from infrastructure.git.client import FakeGitClient
from infrastructure.jira.client import FakeJiraClient
from modules.git.application.service import GitService
from modules.git.infrastructure.repository import InMemoryCommitRepository
from modules.jira.application.service import JiraService
from modules.jira.infrastructure.repository import InMemoryIssueRepository
from shared.logger import get_logger

_logger = get_logger("scheduler.git_sync")


def build_in_memory_pipeline() -> tuple[JiraService, GitService, InMemoryEventStore]:
    """jira+git 를 하나의 버스로 조립한 인메모리 파이프라인."""
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)
    jira = JiraService(FakeJiraClient(), InMemoryIssueRepository(), bus)
    # GitService 는 생성 시 IssueCreated 를 구독한다.
    git = GitService(FakeGitClient(), InMemoryCommitRepository(), bus)
    return jira, git, store


async def _main() -> None:
    jira, git, store = build_in_memory_pipeline()
    await jira.sync()  # IssueCreated 발행 → git 이 매핑 학습
    git_result = await git.sync()  # 커밋 링크
    _logger.info(
        "git_sync.finished",
        commits=git_result.commits_synced,
        links=git_result.links_created,
        events=len(store.events),
    )


if __name__ == "__main__":
    asyncio.run(_main())
