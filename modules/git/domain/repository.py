"""Commit 저장소 추상(포트) + 이슈 매핑.

git 모듈은 다른 모듈을 import 하지 않는다. jira_key→issue_id 매핑은
`IssueCreated` 이벤트를 구독해 학습한 값을 여기에 보관한다(이벤트 기반 협업).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entity import Commit


class CommitRepository(ABC):
    """커밋 영속화 + 이슈 링크 포트. 멱등을 보장한다."""

    @abstractmethod
    async def upsert_commit(self, commit: Commit) -> str:
        """커밋을 upsert 하고 저장소 id 를 반환한다(sha 기준 멱등)."""

    @abstractmethod
    async def link(self, issue_id: str, commit_id: str) -> bool:
        """이슈↔커밋 링크를 만든다. 신규면 True, 이미 있으면 False."""

    @abstractmethod
    async def remember_issue(self, jira_key: str, issue_id: str) -> None:
        """`IssueCreated` 로 학습한 jira_key→issue_id 매핑을 보관한다."""

    @abstractmethod
    async def resolve_issue(self, jira_key: str) -> str | None:
        """jira_key 로 학습된 issue_id 를 조회한다(없으면 None)."""
