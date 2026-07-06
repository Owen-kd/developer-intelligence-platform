"""graph + embedding + search 단위 테스트."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import Event, InMemoryEventBus
from dip_platform.event.event import EventPayload
from modules.embedding.application.service import EmbeddingService
from modules.graph.application.service import GraphService
from modules.graph.infrastructure.repository import InMemoryGraphRepository
from modules.search.application.service import SearchService


@dataclass(frozen=True)
class _Linked(EventPayload):
    issue_id: str
    jira_key: str
    commit_id: str
    sha: str


async def test_graph_builds_from_commits_linked_event() -> None:
    repo = InMemoryGraphRepository()
    bus = InMemoryEventBus()
    service = GraphService(repo, bus)

    await bus.publish(Event("CommitsLinked", _Linked("i-1", "DIP-1", "c-1", "a1b2c3d")))
    await bus.publish(Event("CommitsLinked", _Linked("i-1", "DIP-1", "c-2", "e4f5a6b")))

    shas = await service.impacted_commit_shas("i-1")
    assert shas == ["a1b2c3d", "e4f5a6b"]


def test_embedding_is_deterministic() -> None:
    embedder = EmbeddingService()
    assert embedder.embed("결제 타임아웃") == embedder.embed("결제 타임아웃")


def test_search_ranks_by_similarity() -> None:
    search = SearchService(EmbeddingService())
    search.index("k-pool", "커넥션 풀 고갈로 결제 타임아웃 발생")
    search.index("k-ui", "버튼 색상 변경 요청")

    results = search.query("결제 타임아웃 커넥션 풀", top_k=2)

    assert results[0][0] == "k-pool"  # 가장 유사한 문서가 먼저
    assert results[0][1] >= results[1][1]
