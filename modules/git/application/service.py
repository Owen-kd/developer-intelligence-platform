"""GitService — 커밋 수집 + 이슈 링크 유스케이스.

협업은 이벤트로만 한다: `IssueCreated` 를 구독해 jira_key→issue_id 를 학습하고,
커밋 메시지에서 파싱한 이슈 키가 알려진 이슈면 링크 후 `CommitsLinked` 를 발행한다.
git 모듈은 jira 모듈을 import 하지 않는다(이벤트 필드가 곧 계약이다).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from dip_platform.event import Event, EventBus
from infrastructure.git.client import GitClient
from modules.git.domain.entity import Commit, parse_issue_keys
from modules.git.domain.events import COMMITS_LINKED, CommitsLinkedPayload
from modules.git.domain.repository import CommitRepository
from shared.logger import get_logger

_logger = get_logger("git.service")

# jira 모듈의 이벤트명/필드를 코드로 import 하지 않고 와이어 계약으로만 참조한다.
_ISSUE_CREATED = "IssueCreated"


class _IssueRef(Protocol):
    """`IssueCreated` 페이로드에서 git 이 기대하는 최소 필드(구조적 계약)."""

    issue_id: str
    jira_key: str


@dataclass(frozen=True)
class GitSyncResult:
    """Git 동기화 1회 결과."""

    commits_synced: int
    links_created: int


class GitService:
    """Git 수집/링크를 오케스트레이션한다."""

    def __init__(self, client: GitClient, repo: CommitRepository, bus: EventBus) -> None:
        self._client = client
        self._repo = repo
        self._bus = bus
        bus.subscribe(_ISSUE_CREATED, self._on_issue_created)

    async def _on_issue_created(self, event: Event) -> None:
        ref = cast(_IssueRef, event.payload)
        await self._repo.remember_issue(ref.jira_key, ref.issue_id)

    async def sync(self) -> GitSyncResult:
        commits = await self._client.fetch_commits()
        links_created = 0

        for raw in commits:
            commit = Commit(
                sha=raw.sha,
                author=raw.author,
                message=raw.message,
                committed_at=raw.committed_at,
            )
            commit_id = await self._repo.upsert_commit(commit)

            for jira_key in parse_issue_keys(commit.message):
                issue_id = await self._repo.resolve_issue(jira_key)
                if issue_id is None:
                    continue  # 아직 학습되지 않은 이슈 — 링크 보류
                is_new = await self._repo.link(issue_id, commit_id)
                if is_new:
                    links_created += 1
                    await self._bus.publish(
                        Event(
                            COMMITS_LINKED,
                            CommitsLinkedPayload(issue_id, jira_key, commit_id, commit.sha),
                        )
                    )

        result = GitSyncResult(commits_synced=len(commits), links_created=links_created)
        _logger.info(
            "git.sync.done",
            commits_synced=result.commits_synced,
            links_created=result.links_created,
        )
        return result
