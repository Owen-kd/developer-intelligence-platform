"""하이브리드 검색 융합 — 벡터(의미) + 전문검색(정확어) 결과를 합친다.

Reciprocal Rank Fusion(RRF): 각 결과 리스트에서의 순위만으로 점수를 합산한다
(점수 스케일이 다른 두 검색을 공정하게 결합). 순수 함수 — DB 접근 없음.
"""

from __future__ import annotations

from collections.abc import Sequence

from modules.knowledge.domain.entity import Knowledge

_RRF_K = 60  # RRF 상수(관례값). 낮은 순위 기여를 완만하게 감쇠.


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[str]], k: int = _RRF_K
) -> list[tuple[str, float]]:
    """여러 순위 리스트(문서 id)를 RRF 로 융합해 (id, 점수) 를 점수 내림차순 반환한다.

    score(d) = Σ_lists 1 / (k + rank_d)  (rank 는 0-기반). 동점은 id 로 안정 정렬.
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def hybrid_merge(
    vector_hits: Sequence[tuple[Knowledge, float]],
    keyword_hits: Sequence[tuple[Knowledge, float]],
    limit: int,
) -> list[tuple[Knowledge, float]]:
    """벡터·전문검색 결과를 RRF 로 융합해 상위 `limit` 개를 반환한다.

    반환 점수는 벡터 코사인 유사도(있으면) — 표시/게이트용. 전문검색 단독 히트는 0.0.
    순서는 RRF 융합 순위를 따른다.
    """
    fused = reciprocal_rank_fusion(
        [[k.id for k, _ in vector_hits], [k.id for k, _ in keyword_hits]]
    )
    by_id: dict[str, tuple[Knowledge, float]] = {k.id: (k, score) for k, score in vector_hits}
    for knowledge, _ in keyword_hits:
        by_id.setdefault(knowledge.id, (knowledge, 0.0))
    merged: list[tuple[Knowledge, float]] = []
    for doc_id, _fused_score in fused:
        if doc_id in by_id:
            merged.append(by_id[doc_id])
        if len(merged) >= limit:
            break
    return merged
