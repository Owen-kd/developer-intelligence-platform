"""EmbeddingService — 결정적 로컬 임베딩(외부 모델 불필요).

외부 임베딩 API 로 교체할 경우 infrastructure 어댑터 뒤에 두고 데이터 전송 정책([APR-005])을 따른다.
같은 입력 → 같은 벡터(재현성).
"""

from __future__ import annotations

import math

_DEFAULT_DIM = 32


class EmbeddingService:
    """문자 분포를 고정 차원 벡터로 해싱해 L2 정규화한다(결정적)."""

    def __init__(self, dim: int = _DEFAULT_DIM) -> None:
        self._dim = dim

    def embed(self, text: str) -> tuple[float, ...]:
        buckets = [0.0] * self._dim
        for char in text:
            buckets[ord(char) % self._dim] += 1.0
        norm = math.sqrt(sum(value * value for value in buckets))
        if norm == 0.0:
            return tuple(buckets)
        return tuple(value / norm for value in buckets)
