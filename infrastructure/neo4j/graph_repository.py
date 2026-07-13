"""Neo4j GraphRepository 어댑터 (async Bolt) — ADR-016.

`GraphRepository` 포트를 Cypher 로 구현한다. Neo4j 는 **파생 그래프**(진실원천=Postgres);
멱등 MERGE 로 노드/엣지를 적재한다. 노드는 공통 라벨 `:Entity`(id 유니크 앵커) + kind 라벨
(Issue/Wiki/...)을 함께 붙여 Browser 순회가 자연스럽게 한다.

라벨·관계타입은 Cypher 에서 파라미터화가 불가(식별자)라 문자열 삽입한다 → `_safe_ident` 로
검증(영문/숫자/_ 만)해 주입을 막는다. 값(id/label)은 항상 파라미터.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from neo4j import AsyncGraphDatabase

from modules.graph.domain.model import Edge, Node
from modules.graph.domain.repository import GraphRepository

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class GraphContext:
    """이슈의 그래프 컨텍스트(GraphRAG) — 이웃과 2홉 관련 사안."""

    jira_key: str
    domain: str
    channel: str
    related_wikis: list[str] = field(default_factory=list)  # RELATED_TO 위키 키
    related_issues: list[str] = field(default_factory=list)  # 같은 도메인+채널 위키보유 이슈(2홉)


def _safe_ident(name: str) -> str:
    """Cypher 라벨/관계타입으로 안전한 식별자만 통과(주입 방지). 아니면 예외."""
    if not _IDENT_RE.match(name):
        raise ValueError(f"안전하지 않은 그래프 식별자: {name!r}")
    return name


class Neo4jGraphRepository(GraphRepository):
    """Neo4j 백엔드 그래프 저장소(멱등). 프로세스 종료 시 `aclose()`."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def add_node(self, node: Node) -> None:
        kind = _safe_ident(node.kind)
        query = f"MERGE (n:Entity {{id: $id}}) SET n:{kind}, n.kind = $kind, n.label = $label"
        async with self._driver.session() as session:
            await session.run(query, id=node.id, kind=node.kind, label=node.label)

    async def add_edge(self, edge: Edge) -> None:
        rel = _safe_ident(edge.rel)
        query = (
            "MATCH (a:Entity {id: $src}) "
            "MATCH (b:Entity {id: $dst}) "
            f"MERGE (a)-[:{rel}]->(b)"
        )
        async with self._driver.session() as session:
            await session.run(query, src=edge.src, dst=edge.dst)

    async def add_nodes(self, nodes: list[Node]) -> None:
        """대량 노드 적재(백필용) — kind 별로 묶어 UNWIND MERGE(멱등)."""
        by_kind: dict[str, list[dict[str, str]]] = {}
        for node in nodes:
            by_kind.setdefault(node.kind, []).append({"id": node.id, "label": node.label})
        async with self._driver.session() as session:
            for kind, rows in by_kind.items():
                safe = _safe_ident(kind)
                query = (
                    "UNWIND $rows AS row "
                    f"MERGE (n:Entity {{id: row.id}}) "
                    f"SET n:{safe}, n.kind = $kind, n.label = row.label"
                )
                await session.run(query, rows=rows, kind=kind)

    async def add_edges(self, edges: list[Edge]) -> None:
        """대량 엣지 적재(백필용) — rel 별로 묶어 UNWIND MERGE(멱등). 노드 없으면 그 행은 무시."""
        by_rel: dict[str, list[dict[str, str]]] = {}
        for edge in edges:
            by_rel.setdefault(edge.rel, []).append({"src": edge.src, "dst": edge.dst})
        async with self._driver.session() as session:
            for rel, rows in by_rel.items():
                safe = _safe_ident(rel)
                query = (
                    "UNWIND $rows AS row "
                    "MATCH (a:Entity {id: row.src}) MATCH (b:Entity {id: row.dst}) "
                    f"MERGE (a)-[:{safe}]->(b)"
                )
                await session.run(query, rows=rows)

    async def neighbors(self, node_id: str, kind: str | None = None) -> list[Node]:
        kind_cond = "AND m.kind = $kind" if kind else ""
        query = (
            "MATCH (n:Entity {id: $id})-[]-(m:Entity) "
            f"WHERE m.id <> $id {kind_cond} "
            "RETURN DISTINCT m.id AS id, m.kind AS kind, m.label AS label "
            "ORDER BY id"
        )
        params: dict[str, str] = {"id": node_id}
        if kind:
            params["kind"] = kind
        async with self._driver.session() as session:
            result = await session.run(query, **params)
            rows = [record.data() async for record in result]
        return [Node(id=r["id"], kind=r["kind"], label=r["label"]) for r in rows]

    async def issue_context(self, jira_key: str, limit: int = 8) -> GraphContext | None:
        """이슈의 그래프 컨텍스트(GraphRAG): 도메인/채널 + 관련 위키 + 2홉 관련 사안.

        관련 사안 = 같은 도메인·채널을 공유하며 위키가 있는 다른 이슈(그래프 순회로 발견).
        이슈가 그래프에 없으면 None.
        """
        query = """
        MATCH (i:Issue {label: $key})
        OPTIONAL MATCH (i)-[:IN_DOMAIN]->(d:Domain)
        OPTIONAL MATCH (i)-[:ON_CHANNEL]->(c:Channel)
        OPTIONAL MATCH (i)-[:RELATED_TO]->(rw:Wiki)
        WITH i, d, c, collect(DISTINCT rw.label) AS related_wikis
        OPTIONAL MATCH (i)-[:IN_DOMAIN]->(d)<-[:IN_DOMAIN]-(o:Issue)-[:ON_CHANNEL]->(c),
                       (:Wiki)-[:DESCRIBES]->(o)
        WHERE o <> i
        WITH d, c, related_wikis, collect(DISTINCT o.label)[..$limit] AS related_issues
        RETURN d.label AS domain, c.label AS channel, related_wikis, related_issues
        """
        async with self._driver.session() as session:
            result = await session.run(query, key=jira_key, limit=limit)
            record = await result.single()
        if record is None:
            return None
        return GraphContext(
            jira_key=jira_key,
            domain=record["domain"] or "미상",
            channel=record["channel"] or "공통",
            related_wikis=[w for w in record["related_wikis"] if w],
            related_issues=[o for o in record["related_issues"] if o],
        )

    async def aclose(self) -> None:
        await self._driver.close()
