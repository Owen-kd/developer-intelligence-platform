"""루프3-Push(RelatedKnowledgePush) 단위 테스트 — 유사 위키 자동 연결, 자기 제외."""

from __future__ import annotations

from dataclasses import dataclass

from apps.wiki_pipeline import RelatedKnowledgePush
from dip_platform.event import Event, InMemoryEventBus
from dip_platform.event.event import EventPayload
from infrastructure.embedding.client import FakeEmbedder
from modules.jira.domain.events import ISSUE_CREATED
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.repository import IssueSourceReader


@dataclass(frozen=True)
class _Created(EventPayload):
    issue_id: str


def _wiki(wiki_id: str, issue_id: str) -> Knowledge:
    return Knowledge(
        id=wiki_id, type="wiki", issue_id=issue_id, summary=wiki_id, body={}, sources=()
    )


class _Store:
    def __init__(self, hits: list[tuple[Knowledge, float]]) -> None:
        self._hits = hits
        self.links: list[tuple[str, str, float]] = []

    async def search_semantic(
        self, embedding: list[float], limit: int = 5, types: tuple[str, ...] = ()
    ) -> list[tuple[Knowledge, float]]:
        return self._hits[:limit]

    async def link_related_wiki(self, issue_id: str, wiki_id: str, score: float) -> None:
        self.links.append((issue_id, wiki_id, score))


class _Reader(IssueSourceReader):
    def __init__(self, snapshot: IssueSnapshot) -> None:
        self._snapshot = snapshot

    async def get_snapshot(self, issue_id: str) -> IssueSnapshot | None:
        return self._snapshot if issue_id == self._snapshot.issue_id else None


def _snap() -> IssueSnapshot:
    return IssueSnapshot(
        issue_id="i-1",
        jira_key="PA20-1",
        summary="쿠팡 옵션 오류",
        status="열림",
        priority="High",
        comments=(),
        commit_shas=(),
        source_event_ids=(),
        description="본문",
        components=("쿠팡",),
    )


async def test_push_links_similar_excluding_self() -> None:
    # 검색 결과에 자기 자신(i-1)의 위키 + 다른 이슈 위키들
    hits = [
        (_wiki("w-self", "i-1"), 0.99),
        (_wiki("w-a", "i-2"), 0.90),
        (_wiki("w-b", "i-3"), 0.85),
    ]
    store = _Store(hits)
    bus = InMemoryEventBus()
    push = RelatedKnowledgePush(_Reader(_snap()), store, FakeEmbedder(dim=8), bus, k=2)

    await bus.publish(Event(ISSUE_CREATED, _Created("i-1")))

    assert push.linked == 2
    linked_ids = {wid for _, wid, _ in store.links}
    assert linked_ids == {"w-a", "w-b"}  # 자기 위키(w-self) 제외
    assert "i-1" == store.links[0][0]


async def test_push_skips_out_of_domain() -> None:
    snap = IssueSnapshot(
        issue_id="i-9",
        jira_key="PA20-9",
        summary="배송 지연",
        status="열림",
        priority="Low",
        comments=(),
        commit_shas=(),
        source_event_ids=(),
        components=("배송",),
    )
    store = _Store([(_wiki("w-a", "i-2"), 0.9)])
    bus = InMemoryEventBus()
    push = RelatedKnowledgePush(_Reader(snap), store, FakeEmbedder(dim=8), bus, keywords=("쿠팡",))

    await bus.publish(Event(ISSUE_CREATED, _Created("i-9")))

    assert push.linked == 0
    assert store.links == []
