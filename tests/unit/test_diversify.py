"""검색 다양화(MMR) 단위 테스트 — mmr_select."""

from __future__ import annotations

from modules.knowledge.application.diversify import mmr_select
from modules.knowledge.domain.entity import Knowledge


def _k(kid: str) -> Knowledge:
    return Knowledge(id=kid, type="wiki", issue_id="i", summary=kid, body={}, sources=())


def _ranked(*ids: str) -> list[tuple[Knowledge, float]]:
    # 관련도 내림차순(랭크 기반이라 점수 값 자체는 순위만 의미)
    return [(_k(i), 1.0 - n * 0.01) for n, i in enumerate(ids)]


def test_lambda_one_is_pure_relevance() -> None:
    ranked = _ranked("a", "b", "c")
    emb = {"a": [1.0, 0.0], "b": [1.0, 0.0], "c": [0.0, 1.0]}
    out = mmr_select(ranked, emb, k=2, lambda_=1.0)
    assert [k.id for k, _ in out] == ["a", "b"]  # 다양성 무시 → 원 순위


def test_diversity_suppresses_near_duplicate() -> None:
    # a,b 는 임베딩 동일(같은 주제 중복), c 는 직교(다른 주제).
    ranked = _ranked("a", "b", "c")
    emb = {"a": [1.0, 0.0], "b": [1.0, 0.0], "c": [0.0, 1.0]}
    out = mmr_select(ranked, emb, k=2, lambda_=0.5)
    assert [k.id for k, _ in out] == ["a", "c"]  # b(중복) 대신 c(다양)


def test_preserves_original_relevance_score() -> None:
    ranked = _ranked("a", "b", "c")
    emb = {"a": [1.0, 0.0], "b": [1.0, 0.0], "c": [0.0, 1.0]}
    out = mmr_select(ranked, emb, k=3, lambda_=0.5)
    by_id = {k.id: s for k, s in out}
    assert by_id["a"] == 1.0  # 표시용 원 점수 보존(재계산 안 함)


def test_missing_embeddings_fall_back_to_relevance() -> None:
    ranked = _ranked("a", "b", "c")
    out = mmr_select(ranked, {}, k=2, lambda_=0.5)  # 임베딩 없음 → sim=0 → 순위 유지
    assert [k.id for k, _ in out] == ["a", "b"]


def test_k_larger_than_pool_returns_all() -> None:
    ranked = _ranked("a", "b")
    emb = {"a": [1.0, 0.0], "b": [0.0, 1.0]}
    out = mmr_select(ranked, emb, k=5, lambda_=0.7)
    assert {k.id for k, _ in out} == {"a", "b"}


def test_empty_and_zero_k() -> None:
    assert mmr_select([], {}, k=3) == []
    assert mmr_select(_ranked("a"), {}, k=0) == []
