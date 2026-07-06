"""Incident 도메인 — 근본원인/해결/재발방지 지식(승격 2 산출)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class KnowledgeRef:
    """Incident 승격 입력 — Knowledge 참조(사실 근거)."""

    id: str
    type: str
    summary: str


@dataclass(frozen=True)
class Incident:
    """Incident Library 항목. 근본원인은 사실 근거(sources)에 연결된다."""

    id: str
    issue_id: str
    root_cause: str
    resolution: str
    prevention: str
    sources: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
