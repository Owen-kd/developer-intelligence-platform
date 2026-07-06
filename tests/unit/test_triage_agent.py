"""Triage Agent 파이프라인 테스트 — 분류/검증/폴백/지식축적."""

from __future__ import annotations

from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import ContextBuilder, KnowledgeItem, KnowledgeSource
from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from dip_platform.registry import FilePromptRegistry
from dip_platform.workflow import WorkflowRunner
from dip_platform.workflow.agents.triage import TriageAgent, TriagePipeline
from dip_platform.workflow.events import ISSUE_TRIAGED
from infrastructure.llm.client import FakeLLMClient
from modules.knowledge.application.recorder import AgentKnowledgeRecorder
from modules.knowledge.application.service import PromotionService
from modules.knowledge.domain.events import KNOWLEDGE_PROMOTED
from modules.knowledge.infrastructure.repository import (
    InMemoryIssueSourceReader,
    InMemoryKnowledgeRepository,
)


class _OneItemSource(KnowledgeSource):
    async def fetch(self, task: str, target_id: str) -> list[KnowledgeItem]:
        return [KnowledgeItem("k-1", "결제 타임아웃, 커넥션 풀 고갈", ("evt-1",))]


def _pipeline(
    llm: FakeLLMClient,
) -> tuple[TriagePipeline, InMemoryEventStore, InMemoryKnowledgeRepository]:
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)
    builder = ContextBuilder(_OneItemSource())
    runner = WorkflowRunner(InMemoryAuditLog())
    agent = TriageAgent(llm, FilePromptRegistry())
    pipeline = TriagePipeline(builder, runner, agent, bus)

    repo = InMemoryKnowledgeRepository()
    promotion = PromotionService(InMemoryIssueSourceReader(), repo, bus)
    AgentKnowledgeRecorder(promotion, bus)  # IssueTriaged 구독 → Knowledge 축적
    return pipeline, store, repo


async def test_triage_classifies_and_accumulates_knowledge() -> None:
    llm = FakeLLMClient(
        response='{"category":"bug","priority":"high","confidence":0.9,"rationale":"풀 고갈"}'
    )
    pipeline, store, repo = _pipeline(llm)

    result = await pipeline.run("i-1")

    assert result.output == {"category": "bug", "priority": "high"}
    assert result.confidence == 0.9

    names = [event.name for event in store.events]
    assert ISSUE_TRIAGED in names
    assert KNOWLEDGE_PROMOTED in names  # 분류 결과가 Knowledge 로 축적됨

    knowledge = await repo.list_by_issue("i-1")
    assert any(item.type == "triage" for item in knowledge)


async def test_triage_falls_back_on_invalid_llm_output() -> None:
    pipeline, store, _repo = _pipeline(FakeLLMClient(response="완전히 JSON 아님"))

    result = await pipeline.run("i-1")

    assert result.confidence == 0.0
    assert result.output["category"] == "question"  # 폴백
    assert ISSUE_TRIAGED in [event.name for event in store.events]
