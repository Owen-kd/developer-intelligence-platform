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
