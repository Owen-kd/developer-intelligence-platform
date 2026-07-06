"""Knowledge 포트 — 저장소 + 원천 읽기.

- `KnowledgeRepository`: Knowledge 를 append 지향으로 축적/조회.
- `IssueSourceReader`: Promotion 입력(IssueSnapshot)을 제공하는 읽기 포트.
  구현은 인메모리(데모) 또는 Postgres(issues/comments/commits 조인).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entity import IssueSnapshot, Knowledge


class KnowledgeRepository(ABC):
    """Knowledge Library 포트. 저장은 append(파괴 금지)."""

    @abstractmethod
    async def save(self, knowledge: Knowledge) -> None:
        """Knowledge 를 새 항목으로 축적한다."""

    @abstractmethod
    async def list_by_issue(self, issue_id: str) -> list[Knowledge]:
        """이슈에 연결된 Knowledge 를 생성 순으로 조회한다."""

    @abstractmethod
    async def get(self, knowledge_id: str) -> Knowledge | None:
        """id 로 Knowledge 를 조회한다(없으면 None)."""


class IssueSourceReader(ABC):
    """Promotion 입력을 제공하는 읽기 포트."""

    @abstractmethod
    async def get_snapshot(self, issue_id: str) -> IssueSnapshot | None:
        """이슈의 원천 스냅샷을 조립해 반환한다(없으면 None)."""
