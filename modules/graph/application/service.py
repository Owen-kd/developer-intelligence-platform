"""GraphService — 이벤트로부터 파생 그래프를 구축한다.

`CommitsLinked` 를 구독해 (:Commit)-[:FIXES]->(:Issue) 를 적재한다.
다른 모듈을 import 하지 않고 이벤트 필드(구조적 계약)만 사용한다.
"""

from __future__ import annotations

from typing import Protocol, cast

from dip_platform.event import Event, EventBus
from modules.graph.domain.model import Edge, Node
from modules.graph.domain.repository import GraphRepository
from shared.logger import get_logger

_logger = get_logger("graph.service")

_COMMITS_LINKED = "CommitsLinked"

_ISSUE = "Issue"
_COMMIT = "Commit"
_FIXES = "FIXES"


class _CommitLink(Protocol):
    """`CommitsLinked` 페이로드에서 기대하는 최소 필드."""

    issue_id: str
    jira_key: str
    commit_id: str
    sha: str


class GraphService:
    """이벤트 기반 그래프 구축 + 영향 탐색."""

    def __init__(self, repo: GraphRepository, bus: EventBus) -> None:
        self._repo = repo
        bus.subscribe(_COMMITS_LINKED, self._on_commits_linked)

    async def _on_commits_linked(self, event: Event) -> None:
        link = cast(_CommitLink, event.payload)
        await self._repo.add_node(Node(id=link.issue_id, kind=_ISSUE, label=link.jira_key))
        await self._repo.add_node(Node(id=link.commit_id, kind=_COMMIT, label=link.sha))
        await self._repo.add_edge(Edge(src=link.commit_id, dst=link.issue_id, rel=_FIXES))
        _logger.info("graph.linked", issue_id=link.issue_id, sha=link.sha)

    async def impacted_commit_shas(self, issue_id: str) -> list[str]:
        """이슈에 연결된 커밋 sha 목록(영향 분석 근거)."""
        commits = await self._repo.neighbors(issue_id, kind=_COMMIT)
        return [node.label for node in commits]
