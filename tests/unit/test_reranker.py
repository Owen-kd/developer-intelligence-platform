"""리랭커(cross-encoder 재정렬) 단위 테스트 — FakeReranker + apply_rerank."""

from __future__ import annotations

import pytest

from apps.wiki_pipeline import apply_rerank
from infrastructure.embedding.reranker import FakeReranker
from modules.knowledge.domain.entity import Knowledge


def _k(kid: str, summary: str) -> Knowledge:
    return Knowledge(id=kid, type="wiki", issue_id="i", summary=summary, body={}, sources=())


@pytest.mark.asyncio
async def test_fake_reranker_scores_by_lexical_overlap() -> None:
    scores = await FakeReranker().rerank("쿠팡 옵션 수정", ["쿠팡 옵션 수정 안됨", "무관한 문서"])
    assert scores[0] > scores[1]  # 어휘 겹침 많을수록 높은 점수


@pytest.mark.asyncio
async def test_fake_reranker_empty_documents() -> None:
    assert await FakeReranker().rerank("q", []) == []


@pytest.mark.asyncio
async def test_apply_rerank_reorders_by_relevance() -> None:
    # 융합 순위(코사인 내림차순)는 관련도 낮은 문서를 먼저 두지만, 리랭커가 바로잡는다.
    hits = [
        (_k("a", "결제 환불 지연"), 0.91),  # 융합 1위지만 질의와 무관
        (_k("b", "쿠팡 옵션 수정 안됨"), 0.70),  # 질의와 정확히 겹침
    ]
    reranked = await apply_rerank(FakeReranker(), "쿠팡 옵션 수정", hits)
    assert reranked[0][0].id == "b"  # 리랭커가 관련 문서를 1위로


@pytest.mark.asyncio
async def test_apply_rerank_empty_hits() -> None:
    assert await apply_rerank(FakeReranker(), "q", []) == []
