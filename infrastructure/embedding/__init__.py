"""임베딩 어댑터 패키지 (ADR-009).

`Embedder` 포트와 구현(로컬 fastembed / 결정적 Fake)을 제공한다.
modules/platform 은 포트에만 의존한다(외부 모델 호출은 이 계층에만).
"""

from infrastructure.embedding.client import (
    Embedder,
    FakeEmbedder,
    FastEmbedEmbedder,
    get_embedder,
)

__all__ = ["Embedder", "FakeEmbedder", "FastEmbedEmbedder", "get_embedder"]
