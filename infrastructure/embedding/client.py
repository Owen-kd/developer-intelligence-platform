"""임베딩 포트 + 어댑터 (로컬 fastembed / 결정적 Fake) — ADR-009.

- `Embedder`: 모듈/플랫폼이 의존하는 포트. 벡터 검색을 위한 임베딩 생성만 담당한다.
- `FastEmbedEmbedder`: 로컬 ONNX 모델(fastembed). 외부 API·키 불필요, 사내 데이터 반출 0.
- `FakeEmbedder`: 결정적 해시 임베딩(테스트/오프라인). 모델 다운로드 없이 파이프라인 검증용.

주의:
- e5 계열 모델은 문서/질의에 접두어(`passage:`/`query:`)를 붙여야 성능이 나온다 → 어댑터가 처리.
- fastembed 는 블로킹(CPU) → executor 로 감싼다(coding-guidelines: 블로킹은 executor).
- 프롬프트가 아니므로 하드코딩 금지 규칙과 무관(모델 접두어는 모델 규약).
"""

from __future__ import annotations

import asyncio
import math
import os
import threading
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING

from shared.logger import get_logger

# HuggingFace 'xet' 가속 다운로드 백엔드를 끈다(모델은 최초 1회 캐시되면 그만).
# xet 는 `~/.cache/huggingface/xet/logs` 권한 문제로 간헐 크래시 → 표준 다운로드로 우회.
# (fastembed/huggingface_hub import 전에 설정되어야 효력. setdefault 로 사용자 지정은 존중.)
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

_logger = get_logger("infra.embedding")

if TYPE_CHECKING:
    from fastembed import TextEmbedding


class Embedder(ABC):
    """텍스트 → 벡터 임베딩 포트."""

    @property
    @abstractmethod
    def dim(self) -> int:
        """임베딩 차원(벡터 길이). pgvector 컬럼 차원과 일치해야 한다."""

    @abstractmethod
    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """저장 대상 문서들을 임베딩한다(순서 보존)."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """검색 질의를 임베딩한다."""


class FastEmbedEmbedder(Embedder):
    """로컬 fastembed(ONNX) 어댑터. 모델은 최초 사용 시 지연 로딩(다운로드/캐시)한다."""

    _QUERY_PREFIX = "query: "
    _DOC_PREFIX = "passage: "

    def __init__(self, model_name: str, dim: int, cache_dir: str | None = None) -> None:
        self._model_name = model_name
        self._dim = dim
        # 캐시 경로 고정(휘발성 /tmp 회피). None 이면 fastembed 기본값.
        self._cache_dir = os.path.expanduser(cache_dir) if cache_dir else None
        self._model: TextEmbedding | None = None
        self._lock = threading.Lock()  # executor 스레드 간 지연로딩 경쟁 방지

    def _ensure_model(self) -> TextEmbedding:
        # 이중 검사 락: 동시 임베드(예: WikiAutoGenerator+Push)가 모델을 이중 생성하지 않도록.
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from fastembed import TextEmbedding  # 지연 import(Fake 시 불필요)

                    # 콜드스타트(로딩/다운로드)를 관측한다 — 실패 시 침묵하지 않고 기록(재발 추적).
                    started = time.perf_counter()
                    _logger.info(
                        "embedder.model.loading", model=self._model_name, cache_dir=self._cache_dir
                    )
                    try:
                        self._model = TextEmbedding(
                            model_name=self._model_name, cache_dir=self._cache_dir
                        )
                    except Exception as exc:
                        _logger.error(
                            "embedder.model.load_failed",
                            model=self._model_name,
                            cache_dir=self._cache_dir,
                            error=str(exc),
                        )
                        raise
                    _logger.info(
                        "embedder.model.loaded",
                        model=self._model_name,
                        elapsed_s=round(time.perf_counter() - started, 1),
                    )
        return self._model

    @property
    def dim(self) -> int:
        return self._dim

    async def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        def _work() -> list[list[float]]:
            model = self._ensure_model()
            return [vector.tolist() for vector in model.embed(texts)]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _work)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed([self._DOC_PREFIX + text for text in texts])

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed([self._QUERY_PREFIX + text])
        return vectors[0]


class FakeEmbedder(Embedder):
    """결정적 해시 임베딩(외부 모델 불필요). 파이프라인/단위 테스트용.

    실제 의미 유사도는 약하지만, 같은 텍스트→같은 벡터라 저장/검색 배선 검증에 충분하다.
    """

    def __init__(self, dim: int = 16) -> None:
        self._dim = dim

    @property
    def dim(self) -> int:
        return self._dim

    def _vector(self, text: str) -> list[float]:
        buckets = [0.0] * self._dim
        for char in text:
            buckets[ord(char) % self._dim] += 1.0
        norm = math.sqrt(sum(value * value for value in buckets)) or 1.0
        return [value / norm for value in buckets]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    """설정 기반 프로세스 단일 임베더(warm 인스턴스 재사용) — 매 호출 재생성 방지.

    모든 조립 지점(apps)이 이 팩토리를 공유해 모델을 한 번만 로딩한다.
    """
    from shared.config.settings import get_settings

    settings = get_settings()
    return FastEmbedEmbedder(
        settings.embedding_model, settings.embedding_dim, settings.model_cache_dir
    )
