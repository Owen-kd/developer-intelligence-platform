"""그래프 저장소 포트. 구현: 인메모리(데모) · Neo4j(어댑터, [APR-003] 승인 후)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .model import Edge, Node


class GraphRepository(ABC):
    """노드/엣지 적재 + 이웃 탐색 포트(멱등)."""

    @abstractmethod
    async def add_node(self, node: Node) -> None:
        """노드를 추가한다(같은 id 면 갱신)."""

    @abstractmethod
    async def add_edge(self, edge: Edge) -> None:
        """엣지를 추가한다(중복은 무시)."""

    @abstractmethod
    async def neighbors(self, node_id: str, kind: str | None = None) -> list[Node]:
        """방향 무관하게 연결된 노드를 반환한다(kind 로 필터 가능)."""
