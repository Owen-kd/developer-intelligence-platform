"""루프2 자동화(WikiAutoGenerator) 단위 테스트 — 이벤트→자동 위키, 도메인 필터."""

from __future__ import annotations

import json
from dataclasses import dataclass

from apps.wiki_pipeline import WikiAutoGenerator
from dip_platform.event import Event, InMemoryEventBus
from dip_platform.event.event import EventPayload
from dip_platform.registry import FilePromptRegistry
from infrastructure.embedding.client import FakeEmbedder
from infrastructure.llm.client import FakeLLMClient
from modules.jira.domain.events import ISSUE_CREATED
from modules.knowledge.application.wiki_service import WikiGenerationService
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.repository import IssueSourceReader, KnowledgeRepository


@dataclass(frozen=True)
class _Created(EventPayload):
    issue_id: str


class _Repo(KnowledgeRepository):
    def __init__(self) -> None:
        self.saved: dict[str, Knowledge] = {}
        self.embedded: dict[str, list[float]] = {}

    async def save(self, knowledge: Knowledge) -> None:
        self.saved[knowledge.id] = knowledge

    async def list_by_issue(self, issue_id: str) -> list[Knowledge]:
        return [k for k in self.saved.values() if k.issue_id == issue_id]

    async def get(self, knowledge_id: str) -> Knowledge | None:
        return self.saved.get(knowledge_id)

    async def save_embedding(self, knowledge_id: str, embedding: list[float]) -> None:
        self.embedded[knowledge_id] = embedding


class _Reader(IssueSourceReader):
    def __init__(self, snapshots: dict[str, IssueSnapshot]) -> None:
        self._snapshots = snapshots

    async def get_snapshot(self, issue_id: str) -> IssueSnapshot | None:
        return self._snapshots.get(issue_id)


def _snap(issue_id: str, key: str, components: tuple[str, ...]) -> IssueSnapshot:
    return IssueSnapshot(
        issue_id=issue_id,
        jira_key=key,
        summary=f"{key} 요약",
        status="열림",
        priority="Medium",
        comments=(),
        commit_shas=(),
        source_event_ids=(),
        components=components,
    )


def _wiki_json(_s: str, _u: str) -> str:
    return json.dumps(
        {
            "title": "자동 위키",
            "symptom": "증상",
            "root_cause": "원인",
            "resolution": "해결",
            "code_refs": "",
            "related_issues": [],
            "content": "본문",
        },
        ensure_ascii=False,
    )


def _make(reader: _Reader, repo: _Repo, bus: InMemoryEventBus) -> WikiAutoGenerator:
    service = WikiGenerationService(FakeLLMClient(responder=_wiki_json), FilePromptRegistry(), repo)
    return WikiAutoGenerator(
        service, reader, repo, FakeEmbedder(dim=8), bus, keywords=("상품", "쿠팡")
    )


async def test_auto_generates_wiki_on_issue_created_in_domain() -> None:
    repo = _Repo()
    reader = _Reader({"i-1": _snap("i-1", "PA20-1", ("상품-오류-엔진", "쿠팡"))})
    bus = InMemoryEventBus()
    auto = _make(reader, repo, bus)

    await bus.publish(Event(ISSUE_CREATED, _Created("i-1")))

    assert auto.generated == 1
    assert len(repo.saved) == 1
    wiki = next(iter(repo.saved.values()))
    assert wiki.type == "wiki" and wiki.issue_id == "i-1"
    assert wiki.id in repo.embedded and len(repo.embedded[wiki.id]) == 8


async def test_auto_skips_out_of_domain_issue() -> None:
    repo = _Repo()
    reader = _Reader({"i-2": _snap("i-2", "PA20-2", ("주문-오류", "배송"))})
    bus = InMemoryEventBus()
    auto = _make(reader, repo, bus)

    await bus.publish(Event(ISSUE_CREATED, _Created("i-2")))

    assert auto.generated == 0
    assert repo.saved == {}
