"""GraphRepository 인메모리 구현.

Neo4j 어댑터는 같은 포트로 추가한다(드라이버 의존성은 [APR-003] 승인 후).
"""

from __future__ import annotations

from modules.graph.domain.model import Edge, Node
from modules.graph.domain.repository import GraphRepository


class InMemoryGraphRepository(GraphRepository):
    """프로세스 메모리 기반 그래프."""

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: set[Edge] = set()

    async def add_node(self, node: Node) -> None:
        self._nodes[node.id] = node

    async def add_edge(self, edge: Edge) -> None:
        self._edges.add(edge)

    async def neighbors(self, node_id: str, kind: str | None = None) -> list[Node]:
        neighbor_ids: list[str] = []
        for edge in self._edges:
            if edge.src == node_id:
                neighbor_ids.append(edge.dst)
            elif edge.dst == node_id:
                neighbor_ids.append(edge.src)
        # 결정적 순서: 노드 id 정렬
        result: list[Node] = []
        for nid in sorted(set(neighbor_ids)):
            node = self._nodes.get(nid)
            if node is not None and (kind is None or node.kind == kind):
                result.append(node)
        return result
