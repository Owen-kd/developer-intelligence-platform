"""GraphService IssueClassified 증분 반영 단위 테스트 (인메모리 그래프). ADR-016 2단계."""

from __future__ import annotations

import pytest

from dip_platform.event import Event, InMemoryEventBus
from modules.graph.application.service import GraphService
from modules.graph.infrastructure.repository import InMemoryGraphRepository
from modules.knowledge.domain.events import ISSUE_CLASSIFIED, IssueClassifiedPayload


@pytest.mark.asyncio
async def test_classified_adds_issue_domain_channel() -> None:
    bus = InMemoryEventBus()
    repo = InMemoryGraphRepository()
    GraphService(repo, bus)

    await bus.publish(
        Event(ISSUE_CLASSIFIED, IssueClassifiedPayload("i1", "PA20-1", "product", "쿠팡", "rule"))
    )

    neighbors = await repo.neighbors("i1")
    by_kind = {n.kind: n.label for n in neighbors}
    assert by_kind.get("Domain") == "product"
    assert by_kind.get("Channel") == "쿠팡"


@pytest.mark.asyncio
async def test_unknown_domain_and_common_channel_skipped() -> None:
    bus = InMemoryEventBus()
    repo = InMemoryGraphRepository()
    GraphService(repo, bus)

    await bus.publish(
        Event(ISSUE_CLASSIFIED, IssueClassifiedPayload("i2", "X-1", "미상", "공통", "rule"))
    )

    # 이슈 노드는 생기지만 도메인/채널 엣지는 없음(미상/공통은 노드화 안 함)
    assert await repo.neighbors("i2") == []
