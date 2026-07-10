"""검색 결과 다양화(MMR) — 같은 주제 계열의 중복 노출을 억제한다(비파괴, 순수).

같은 도메인 위키는 임베딩 바닥 유사도가 높아(측정: ≥0.90 쌍이 다수) 순위 상위가
한 주제로 도배되기 쉽다. MMR(Maximal Marginal Relevance)로 관련도와 다양성을 절충해
top-k 를 고르면, 관련성을 크게 해치지 않으면서 서로 다른 주제를 함께 보여준다.

관련도는 **입력 순위(랭크)** 로 본다 — 리랭커 로짓/코사인 등 서로 다른 척도에 안전하다.
다양성도 같은 이유로 **후보 풀 안에서 상대화**한다: 같은 도메인 위키는 절대 코사인이
모두 ~0.91(측정 스프레드 ~0.03)로 몰려 절대값 페널티는 거의 상수라 재정렬을 못 만든다.
그래서 각 선택 단계에서 남은 후보들의 max_sim 을 min-max 정규화해, "가장 겹치는 후보=1.0,
가장 안 겹치는 후보=0.0" 로 만든다(척도 무관). 임베딩 없는 항목은 sim=0(최대 다양)으로 취급.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from modules.knowledge.domain.entity import Knowledge


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """두 벡터의 코사인 유사도. 길이 불일치/영벡터는 0.0(무관)으로 방어."""
    if len(a) != len(b):
        return 0.0
    num = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return num / (na * nb)


def mmr_select(
    ranked: list[tuple[Knowledge, float]],
    embeddings: Mapping[str, Sequence[float]],
    k: int,
    lambda_: float = 0.7,
) -> list[tuple[Knowledge, float]]:
    """MMR 로 top-k 를 선정한다(원 관련도 점수는 표시용으로 보존).

    lambda_=1.0 이면 순수 관련도(원 순위 그대로), 0.0 이면 순수 다양성.
    관련도는 입력 순위 기반(1위=1.0 ~ 하위로 감소)이라 점수 척도에 무관하게 안정적이다.
    동점은 입력 순서(더 관련 있는 쪽)를 유지해 결정적이다.
    """
    if k <= 0 or not ranked:
        return ranked[: max(k, 0)]
    n = len(ranked)
    rel = {kn.id: (n - i) / n for i, (kn, _) in enumerate(ranked)}

    remaining = list(ranked)
    selected: list[tuple[Knowledge, float]] = [remaining.pop(0)]  # 최상위는 항상 선택
    while remaining and len(selected) < k:
        # 1) 남은 후보별 "이미 선택된 것과의 최대 유사도"
        sims = [_max_sim_to(kn.id, selected, embeddings) for kn, _ in remaining]
        # 2) 풀 안에서 min-max 정규화(절대 코사인이 몰려 있어도 상대 다양성이 드러나도록)
        lo, hi = min(sims), max(sims)
        span = hi - lo
        # 3) MMR = λ·관련도 − (1−λ)·정규화 유사도
        best_idx = 0
        best_mmr = -math.inf
        for idx, (kn, _score) in enumerate(remaining):
            norm_sim = (sims[idx] - lo) / span if span > 0 else 0.0
            mmr = lambda_ * rel[kn.id] - (1.0 - lambda_) * norm_sim
            if mmr > best_mmr:  # strict > → 동점 시 먼저 온(더 관련) 항목 유지
                best_mmr = mmr
                best_idx = idx
        selected.append(remaining.pop(best_idx))
    return selected[:k]


def _max_sim_to(
    kid: str,
    selected: list[tuple[Knowledge, float]],
    embeddings: Mapping[str, Sequence[float]],
) -> float:
    """후보 kid 와 이미 선택된 항목들 사이의 최대 코사인(임베딩 없으면 0.0)."""
    emb = embeddings.get(kid)
    if not emb:
        return 0.0
    best = 0.0
    for skn, _s in selected:
        semb = embeddings.get(skn.id)
        if semb:
            best = max(best, _cosine(emb, semb))
    return best
