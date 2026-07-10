"""하이브리드 융합(RRF + hybrid_merge) 단위 테스트."""

from __future__ import annotations

from modules.knowledge.application.fusion import hybrid_merge, reciprocal_rank_fusion
from modules.knowledge.domain.entity import Knowledge


def _k(kid: str) -> Knowledge:
    return Knowledge(id=kid, type="wiki", issue_id="i", summary=kid, body={}, sources=())


def test_rrf_rewards_appearing_in_both_lists() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "x", "y"]])
    ids = [doc_id for doc_id, _ in fused]
    assert ids[0] == "b"  # 두 리스트 모두 상위 → 최상


def test_rrf_stable_tiebreak_by_id() -> None:
    fused = reciprocal_rank_fusion([["a"], ["b"]])  # 둘 다 rank0 → 동점
    assert [doc_id for doc_id, _ in fused] == ["a", "b"]


def test_hybrid_merge_orders_by_fusion_and_keeps_cosine() -> None:
    va, vb = _k("a"), _k("b")
    vector = [(va, 0.9), (vb, 0.7)]
    keyword = [(vb, 0.5)]  # b 가 양쪽 → 융합 최상
    merged = hybrid_merge(vector, keyword, limit=5)
    assert merged[0][0].id == "b"
    assert merged[0][1] == 0.7  # 벡터 코사인 보존


def test_hybrid_merge_keyword_only_hit_gets_zero_cosine() -> None:
    merged = hybrid_merge([(_k("a"), 0.9)], [(_k("b"), 0.4)], limit=5)
    by_id = {k.id: s for k, s in merged}
    assert by_id["b"] == 0.0  # 정확어 단독 히트 → 코사인 미상(0.0)


def test_hybrid_merge_respects_limit() -> None:
    vector = [(_k(x), 0.5) for x in ("a", "b", "c", "d")]
    merged = hybrid_merge(vector, [], limit=2)
    assert len(merged) == 2
