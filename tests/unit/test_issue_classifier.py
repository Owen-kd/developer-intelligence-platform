"""신규 이슈 자동 facet 분류(IssueFacetClassifier) 단위 테스트 — 이벤트 구동, LLM 0."""

from __future__ import annotations

import pytest

from apps.wiki_pipeline import IssueFacetClassifier
from dip_platform.event import Event, InMemoryEventBus
from modules.jira.domain.events import ISSUE_CREATED, IssueCreatedPayload
from modules.knowledge.domain.entity import IssueSnapshot
from modules.knowledge.domain.events import ISSUE_CLASSIFIED
from modules.knowledge.infrastructure.repository import InMemoryIssueSourceReader


class _FakeSink:
    def __init__(self, existing: set[str] | None = None) -> None:
        self.saved: list[tuple[str, dict[str, str], str]] = []
        self._existing = existing or set()

    async def save_facets(
        self, issue_id: str, facets: dict[str, str], method: str = "rule"
    ) -> None:
        self.saved.append((issue_id, facets, method))
        self._existing.add(issue_id)

    async def facets_exist(self, issue_id: str) -> bool:
        return issue_id in self._existing


def _snapshot() -> IssueSnapshot:
    return IssueSnapshot(
        issue_id="i1",
        jira_key="PA20-19864",
        summary="[쿠팡] 상품옵션 수정 오류",
        status="열림",
        priority="P2",
        comments=(),
        commit_shas=(),
        source_event_ids=(),
        components=("상품-오류-엔진", "쿠팡"),
    )


@pytest.mark.asyncio
async def test_issue_created_triggers_rule_classification() -> None:
    bus = InMemoryEventBus()
    reader = InMemoryIssueSourceReader()
    reader.add(_snapshot())
    sink = _FakeSink()
    classifier = IssueFacetClassifier(reader, sink, bus)

    emitted: list[str] = []
    bus.subscribe(ISSUE_CLASSIFIED, lambda e: _record(emitted, e))

    await bus.publish(Event(ISSUE_CREATED, IssueCreatedPayload("i1", "PA20-19864")))

    assert classifier.classified == 1
    assert len(sink.saved) == 1
    issue_id, facets, method = sink.saved[0]
    assert issue_id == "i1" and method == "rule"
    assert facets["domain"] == "product" and facets["channel"] == "쿠팡"
    assert emitted == ["PA20-19864"]  # IssueClassified 발행됨


async def _record(bucket: list[str], event: Event) -> None:
    bucket.append(getattr(event.payload, "jira_key", "?"))


@pytest.mark.asyncio
async def test_missing_snapshot_is_skipped() -> None:
    bus = InMemoryEventBus()
    sink = _FakeSink()
    classifier = IssueFacetClassifier(InMemoryIssueSourceReader(), sink, bus)
    await bus.publish(Event(ISSUE_CREATED, IssueCreatedPayload("ghost", "X-1")))
    assert classifier.classified == 0 and sink.saved == []


@pytest.mark.asyncio
async def test_already_classified_is_skipped_idempotent() -> None:
    # 이미 분류된 이슈(예: LLM 보강분)는 규칙 재분류가 덮지 않는다(at-least-once 재전송 방어).
    bus = InMemoryEventBus()
    reader = InMemoryIssueSourceReader()
    reader.add(_snapshot())
    sink = _FakeSink(existing={"i1"})
    classifier = IssueFacetClassifier(reader, sink, bus)
    await bus.publish(Event(ISSUE_CREATED, IssueCreatedPayload("i1", "PA20-19864")))
    assert classifier.classified == 0 and sink.saved == []
