"""Neo4j 지식 그래프 백필 — Postgres(진실원천) → Neo4j(파생 그래프). ADR-016 1단계.

노드: Issue / Wiki / Commit / Domain / Channel / Component
엣지: (Commit)-[:FIXES]->(Issue) · (Wiki)-[:DESCRIBES]->(Issue) · (Issue)-[:IN_DOMAIN]->(Domain)
      · (Issue)-[:ON_CHANNEL]->(Channel) · (Issue)-[:IN_COMPONENT]->(Component)
      · (Issue)-[:RELATED_TO]->(Wiki)
멱등(MERGE) — 반복 실행해도 같은 그래프. Neo4j 유실 시 이 스크립트로 복원.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text

from infrastructure.neo4j.graph_repository import Neo4jGraphRepository
from infrastructure.postgres import connection as pg
from modules.graph.domain.model import Edge, Node
from shared.config.settings import get_settings
from shared.logger import get_logger

_logger = get_logger("graph.backfill")

_UNKNOWN, _COMMON = "미상", "공통"


@dataclass
class BackfillResult:
    nodes: int
    edges: int


def _domain_id(name: str) -> str:
    return f"domain:{name}"


def _channel_id(name: str) -> str:
    return f"channel:{name}"


def _component_id(name: str) -> str:
    return f"component:{name}"


async def backfill_graph() -> BackfillResult:
    """Postgres 관계를 Neo4j 노드/엣지로 적재하고 개수를 반환한다."""
    settings = get_settings()
    nodes: list[Node] = []
    edges: list[Edge] = []
    domains: set[str] = set()
    channels: set[str] = set()
    components: set[str] = set()

    async with pg.get_engine().connect() as conn:
        # 이슈 노드
        issues = (await conn.execute(text("SELECT id::text, jira_key FROM issues"))).all()
        for row in issues:
            nodes.append(Node(id=row.id, kind="Issue", label=row.jira_key))

        # 위키 노드 + DESCRIBES
        wikis = (
            await conn.execute(
                text(
                    "SELECT k.id::text AS wid, k.issue_id::text AS iid, i.jira_key "
                    "FROM knowledge k JOIN issues i ON i.id = k.issue_id WHERE k.type='wiki'"
                )
            )
        ).all()
        for row in wikis:
            nodes.append(Node(id=row.wid, kind="Wiki", label=row.jira_key))
            edges.append(Edge(src=row.wid, dst=row.iid, rel="DESCRIBES"))

        # 커밋 노드 + FIXES
        commits = (
            await conn.execute(
                text(
                    "SELECT c.id::text AS cid, c.sha, ic.issue_id::text AS iid "
                    "FROM commits c JOIN issue_commits ic ON ic.commit_id = c.id"
                )
            )
        ).all()
        for row in commits:
            nodes.append(Node(id=row.cid, kind="Commit", label=row.sha[:12]))
            edges.append(Edge(src=row.cid, dst=row.iid, rel="FIXES"))

        # facet: 도메인/채널 노드 + 엣지
        facets = (
            await conn.execute(
                text("SELECT issue_id::text AS iid, domain, channel FROM issue_facets")
            )
        ).all()
        for row in facets:
            if row.domain and row.domain != _UNKNOWN:
                domains.add(row.domain)
                edges.append(Edge(src=row.iid, dst=_domain_id(row.domain), rel="IN_DOMAIN"))
            if row.channel and row.channel != _COMMON:
                channels.add(row.channel)
                edges.append(Edge(src=row.iid, dst=_channel_id(row.channel), rel="ON_CHANNEL"))

        # 컴포넌트 노드 + IN_COMPONENT
        comps = (
            await conn.execute(
                text(
                    "SELECT i.id::text AS iid, c AS comp FROM issues i, "
                    "jsonb_array_elements_text(i.components) c"
                )
            )
        ).all()
        for row in comps:
            components.add(row.comp)
            edges.append(Edge(src=row.iid, dst=_component_id(row.comp), rel="IN_COMPONENT"))

        # RELATED_TO (issue_related_wiki)
        related = (
            await conn.execute(
                text("SELECT issue_id::text AS iid, wiki_id::text AS wid FROM issue_related_wiki")
            )
        ).all()
        for row in related:
            edges.append(Edge(src=row.iid, dst=row.wid, rel="RELATED_TO"))

    for name in sorted(domains):
        nodes.append(Node(id=_domain_id(name), kind="Domain", label=name))
    for name in sorted(channels):
        nodes.append(Node(id=_channel_id(name), kind="Channel", label=name))
    for name in sorted(components):
        nodes.append(Node(id=_component_id(name), kind="Component", label=name))

    repo = Neo4jGraphRepository(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        await repo.add_nodes(nodes)
        await repo.add_edges(edges)
    finally:
        await repo.aclose()

    _logger.info("graph.backfill.done", nodes=len(nodes), edges=len(edges))
    return BackfillResult(nodes=len(nodes), edges=len(edges))
