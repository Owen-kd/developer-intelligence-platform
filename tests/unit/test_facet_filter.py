"""검색 facet 필터 SQL 조건 빌더 단위 테스트 — _facet_condition (순수, 주입 방지)."""

from __future__ import annotations

from modules.knowledge.infrastructure.repository import _facet_condition


def test_empty_filters_no_condition() -> None:
    assert _facet_condition(None) == ("", {})
    assert _facet_condition({}) == ("", {})


def test_builds_parameterized_condition() -> None:
    cond, params = _facet_condition({"domain": "product", "channel": "쿠팡"})
    assert "EXISTS (SELECT 1 FROM issue_facets f" in cond
    assert "f.domain = :fct_domain" in cond
    assert "f.channel = :fct_channel" in cond
    assert params == {"fct_domain": "product", "fct_channel": "쿠팡"}


def test_rejects_non_whitelisted_axis() -> None:
    # 화이트리스트 밖 축(임의 컬럼명)은 무시 → SQL 주입 방지
    cond, params = _facet_condition({"id": "1", "domain": "order", "drop": "x"})
    assert "f.id" not in cond and "drop" not in cond
    assert params == {"fct_domain": "order"}


def test_drops_empty_values() -> None:
    cond, params = _facet_condition({"domain": "", "issue_type": "오류"})
    assert params == {"fct_issue_type": "오류"}
