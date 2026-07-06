"""Incident 포트 — 저장소 + Knowledge 읽기.

incident 모듈은 knowledge 모듈을 직접 import 하지 않는다. Knowledge 조회는
`KnowledgeReader` 포트로 추상화하고, 어댑터는 조립 계층(apps)이 제공한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .entity import Incident, KnowledgeRef


class IncidentRepository(ABC):
    """Incident Library 포트(append 지향)."""

    @abstractmethod
    async def save(self, incident: Incident) -> None:
        """Incident 를 축적한다."""

    @abstractmethod
    async def list_all(self) -> list[Incident]:
        """모든 Incident 를 생성 순으로 조회한다."""


class KnowledgeReader(ABC):
    """Incident 승격 입력을 제공하는 Knowledge 읽기 포트."""

    @abstractmethod
    async def refs_by_issue(self, issue_id: str) -> list[KnowledgeRef]:
        """이슈에 축적된 Knowledge 참조 목록을 반환한다."""
