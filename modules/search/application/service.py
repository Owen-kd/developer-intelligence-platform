"""SearchService — 임베딩 기반 최소 의미 검색.

임베더는 로컬 Protocol 로 주입한다(모듈 간 직접 import 금지 — 조립은 apps 에서).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol


class Embedder(Protocol):
    """텍스트를 벡터로 변환하는 구조적 계약."""

    def embed(self, text: str) -> Sequence[float]: ...


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


class SearchService:
    """문서를 임베딩해 색인하고, 질의와의 코사인 유사도로 랭킹한다."""

    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._index: dict[str, Sequence[float]] = {}

    def index(self, doc_id: str, text: str) -> None:
        self._index[doc_id] = self._embedder.embed(text)

    def query(self, text: str, top_k: int = 5) -> list[tuple[str, float]]:
        vector = self._embedder.embed(text)
        scored = [(doc_id, _cosine(vector, vec)) for doc_id, vec in self._index.items()]
        # 점수 내림차순, 동점은 doc_id 오름차순(결정적).
        scored.sort(key=lambda pair: (-pair[1], pair[0]))
        return scored[:top_k]
