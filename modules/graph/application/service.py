"""GraphService — 이벤트로부터 파생 그래프를 구축한다.

`CommitsLinked` → (:Commit)-[:FIXES]->(:Issue), `IssueClassified` → 이슈+도메인/채널 엣지.
다른 모듈을 import 하지 않고 이벤트 필드(구조적 계약)만 사용한다.
"""

from __future__ import annotations

from typing import Protocol, cast

from dip_platform.event import Event, EventBus
from modules.graph.domain.model import (
    Edge,
    Node,
    channel_node_id,
    domain_node_id,
)
from modules.graph.domain.repository import GraphRepository
from shared.logger import get_logger

_logger = get_logger("graph.service")

_COMMITS_LINKED = "CommitsLinked"
_ISSUE_CLASSIFIED = "IssueClassified"

_ISSUE = "Issue"
_COMMIT = "Commit"
_DOMAIN = "Domain"
_CHANNEL = "Channel"
_FIXES = "FIXES"
_IN_DOMAIN = "IN_DOMAIN"
_ON_CHANNEL = "ON_CHANNEL"
_UNKNOWN, _COMMON = "미상", "공통"


class _CommitLink(Protocol):
    """`CommitsLinked` 페이로드에서 기대하는 최소 필드."""

    issue_id: str
    jira_key: str
    commit_id: str
    sha: str


class _IssueClassified(Protocol):
    """`IssueClassified` 페이로드에서 기대하는 최소 필드(ADR-015)."""

    issue_id: str
    jira_key: str
    domain: str
    channel: str


class GraphService:
    """이벤트 기반 그래프 구축 + 영향 탐색."""

    def __init__(self, repo: GraphRepository, bus: EventBus) -> None:
        self._repo = repo
        bus.subscribe(_COMMITS_LINKED, self._on_commits_linked)
        bus.subscribe(_ISSUE_CLASSIFIED, self._on_issue_classified)

    async def _on_commits_linked(self, event: Event) -> None:
        link = cast(_CommitLink, event.payload)
        await self._repo.add_node(Node(id=link.issue_id, kind=_ISSUE, label=link.jira_key))
        await self._repo.add_node(Node(id=link.commit_id, kind=_COMMIT, label=link.sha))
        await self._repo.add_edge(Edge(src=link.commit_id, dst=link.issue_id, rel=_FIXES))
        _logger.info("graph.linked", issue_id=link.issue_id, sha=link.sha)

    async def _on_issue_classified(self, event: Event) -> None:
        """신규 이슈 분류 → 이슈 노드 + 도메인/채널 노드·엣지를 그래프에 반영(증분 최신화)."""
        payload = cast(_IssueClassified, event.payload)
        await self._repo.add_node(
            Node(id=payload.issue_id, kind=_ISSUE, label=payload.jira_key)
        )
        if payload.domain and payload.domain != _UNKNOWN:
            node_id = domain_node_id(payload.domain)
            await self._repo.add_node(Node(id=node_id, kind=_DOMAIN, label=payload.domain))
            await self._repo.add_edge(Edge(src=payload.issue_id, dst=node_id, rel=_IN_DOMAIN))
        if payload.channel and payload.channel != _COMMON:
            node_id = channel_node_id(payload.channel)
            await self._repo.add_node(Node(id=node_id, kind=_CHANNEL, label=payload.channel))
            await self._repo.add_edge(Edge(src=payload.issue_id, dst=node_id, rel=_ON_CHANNEL))
        _logger.info("graph.classified", jira_key=payload.jira_key, domain=payload.domain)

    async def impacted_commit_shas(self, issue_id: str) -> list[str]:
        """이슈에 연결된 커밋 sha 목록(영향 분석 근거)."""
        commits = await self._repo.neighbors(issue_id, kind=_COMMIT)
        return [node.label for node in commits]
