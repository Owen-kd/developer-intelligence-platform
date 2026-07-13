"""그래프 도메인 모델 — 노드/엣지.

Neo4j 는 파생 그래프(진실 원천은 Postgres)다([.ai/architecture/database-design.md]).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    """그래프 노드. kind 예: Issue, Commit, File."""

    id: str
    kind: str
    label: str


@dataclass(frozen=True)
class Edge:
    """방향 있는 관계. rel 예: FIXES, TOUCHES, DEPENDS_ON."""

    src: str
    dst: str
    rel: str


# facet 노드 id 규약 — 백필과 증분 동기화가 같은 노드를 가리키도록 한 곳에서 정의(ADR-016).
def domain_node_id(name: str) -> str:
    return f"domain:{name}"


def channel_node_id(name: str) -> str:
    return f"channel:{name}"


def component_node_id(name: str) -> str:
    return f"component:{name}"
