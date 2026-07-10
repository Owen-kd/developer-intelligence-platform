"""리랭커 포트 + 어댑터 (로컬 cross-encoder / 결정적 Fake) — 하이브리드 검색 재정렬.

하이브리드(벡터+전문검색) 후보를 cross-encoder 로 질의-문서 쌍 채점해 재정렬한다.
bi-encoder(임베딩)보다 정밀하지만 느려서 상위 소수 후보에만 적용한다.
"""

from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastembed.rerank.cross_encoder import TextCrossEncoder


class Reranker(ABC):
    """질의-문서 관련도 재정렬 포트."""

    @abstractmethod
    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        """각 문서의 관련도 점수(높을수록 관련) — 입력과 같은 순서·길이로 반환."""


class FastEmbedReranker(Reranker):
    """로컬 fastembed cross-encoder. 모델은 최초 사용 시 지연 로딩(다운로드/캐시)."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model: TextCrossEncoder | None = None
        self._lock = threading.Lock()

    def _ensure_model(self) -> TextCrossEncoder:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from fastembed.rerank.cross_encoder import TextCrossEncoder

                    self._model = TextCrossEncoder(model_name=self._model_name)
        return self._model

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []

        def _work() -> list[float]:
            model = self._ensure_model()
            return [float(score) for score in model.rerank(query, documents)]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _work)


class FakeReranker(Reranker):
    """결정적 Fake — 질의·문서 어휘 겹침 수를 점수로(테스트/오프라인)."""

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        query_tokens = set(query.lower().split())
        return [float(len(query_tokens & set(doc.lower().split()))) for doc in documents]


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    """설정 기반 프로세스 단일 리랭커(warm 인스턴스 재사용)."""
    from shared.config.settings import get_settings

    return FastEmbedReranker(get_settings().reranker_model)
