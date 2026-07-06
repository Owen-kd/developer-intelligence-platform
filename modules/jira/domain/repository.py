"""Issue 저장소 추상(포트). 구현은 infrastructure 계층에서."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entity import Comment, Issue


class IssueRepository(ABC):
    """이슈/코멘트 영속화 포트. 멱등 upsert 를 보장해야 한다."""

    @abstractmethod
    async def upsert_issue(self, issue: Issue) -> str:
        """이슈를 upsert 하고 저장소 식별자(id)를 반환한다.

        `jira_key` 기준 멱등: 재호출해도 중복 생성하지 않는다.
        """

    @abstractmethod
    async def upsert_comment(self, issue_id: str, jira_key: str, comment: Comment) -> bool:
        """코멘트를 upsert 한다. 신규로 추가되면 True, 이미 존재하면 False.

        `(issue_id, external_id)` 기준 멱등.
        """

    @abstractmethod
    async def get_issue(self, jira_key: str) -> Issue | None:
        """jira_key 로 이슈를 조회한다(없으면 None)."""

    @abstractmethod
    async def list_issues(self) -> list[Issue]:
        """모든 이슈를 jira_key 순으로 조회한다."""
