"""gap 판정(is_gap) 단위 테스트 — 되먹임 씨앗 로직."""

from __future__ import annotations

from apps.wiki_pipeline import is_gap
from modules.knowledge.domain.entity import Knowledge


def _k() -> Knowledge:
    return Knowledge(id="k", type="wiki", issue_id="i", summary="s", body={}, sources=())


def test_no_hits_is_gap() -> None:
    assert is_gap([]) is True


def test_low_score_is_gap() -> None:
    assert is_gap([(_k(), 0.5)], threshold=0.75) is True


def test_strong_hit_is_not_gap() -> None:
    assert is_gap([(_k(), 0.9)], threshold=0.75) is False
