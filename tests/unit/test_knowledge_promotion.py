"""Knowledge 승격 단위 테스트 — 출처 보존/append/검증/이벤트."""

from __future__ import annotations

from dataclasses import replace

import pytest

from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from modules.knowledge.application.service import PromotionService
from modules.knowledge.domain.entity import IssueSnapshot
from modules.knowledge.domain.events import KNOWLEDGE_PROMOTED
from modules.knowledge.infrastructure.repository import (
    InMemoryIssueSourceReader,
    InMemoryKnowledgeRepository,
)
from shared.exceptions import NotFoundError


def _snapshot() -> IssueSnapshot:
    return IssueSnapshot(
        issue_id="i-1",
        jira_key="DIP-1",
        summary="결제 API 간헐적 타임아웃",
        status="In Progress",
        priority="High",
        comments=("피크에 커넥션 풀 고갈",),
        commit_shas=("a1b2c3d",),
        source_event_ids=("evt-1", "evt-2"),
    )


def _service(
    snapshot: IssueSnapshot | None,
) -> tuple[PromotionService, InMemoryKnowledgeRepository, InMemoryEventStore]:
    reader = InMemoryIssueSourceReader()
    if snapshot is not None:
        reader.add(snapshot)
    repo = InMemoryKnowledgeRepository()
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)
    return PromotionService(reader, repo, bus), repo, store


async def test_promote_preserves_sources_and_publishes() -> None:
    service, _repo, store = _service(_snapshot())

    knowledge = await service.promote_issue("i-1")

    assert knowledge.sources == ("evt-1", "evt-2")  # 출처 보존
    assert "DIP-1" in knowledge.summary
    assert [event.name for event in store.events] == [KNOWLEDGE_PROMOTED]


async def test_promotion_is_append_not_overwrite() -> None:
    service, repo, _store = _service(_snapshot())

    await service.promote_issue("i-1")
    await service.promote_issue("i-1")

    items = await repo.list_by_issue("i-1")
    assert len(items) == 2  # 파괴가 아니라 축적


async def test_sources_fallback_keeps_provenance() -> None:
    service, _repo, _store = _service(replace(_snapshot(), source_event_ids=()))

    knowledge = await service.promote_issue("i-1")

    assert knowledge.sources  # 이벤트가 없어도 출처는 비지 않는다
    assert knowledge.sources[0] == "issue:DIP-1"


async def test_promote_missing_snapshot_raises() -> None:
    service, _repo, _store = _service(None)

    with pytest.raises(NotFoundError):
        await service.promote_issue("nope")
