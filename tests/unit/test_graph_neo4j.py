"""Neo4j 어댑터 순수부 단위 테스트 — 식별자 검증(주입 방지). ADR-016."""

from __future__ import annotations

import pytest

from infrastructure.neo4j.graph_repository import _safe_ident


def test_accepts_valid_identifiers() -> None:
    for name in ("Issue", "Wiki", "IN_DOMAIN", "FIXES", "_x1"):
        assert _safe_ident(name) == name


def test_rejects_injection_attempts() -> None:
    for bad in ("Issue) DELETE n //", "a-b", "1abc", "라벨", "n {x:1}", ""):
        with pytest.raises(ValueError):
            _safe_ident(bad)
