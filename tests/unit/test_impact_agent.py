"""Impact Agent 파이프라인 테스트 — 그래프 근거/영향커밋/지식축적."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import ContextBuilder, KnowledgeItem, KnowledgeSource
from dip_platform.event import Event, InMemoryEventBus, InMemoryEventStore
from dip_platform.event.event import EventPayload
from dip_platform.registry import FilePromptRegistry
from dip_platform.workflow import WorkflowRunner
from dip_platform.workflow.agents.impact import ImpactAgent, ImpactPipeline
from dip_platform.workflow.events import IMPACT_ANALYZED, ImpactAnalyzedPayload
from infrastructure.llm.client import FakeLLMClient
from modules.graph.application.service import GraphService
from modules.graph.infrastructure.impact_source import GraphImpactSource
from modules.graph.infrastructure.repository import InMemoryGraphRepository
from modules.knowledge.application.recorder import AgentKnowledgeRecorder
from modules.knowledge.application.service import PromotionService
from modules.knowledge.infrastructure.repository import (
    InMemoryIssueSourceReader,
    InMemoryKnowledgeRepository,
)


@dataclass(frozen=True)
class _Linked(EventPayload):
    issue_id: str
    jira_key: str
    commit_id: str
    sha: str


class _OneItemSource(KnowledgeSource):
    async def fetch(self, task: str, target_id: str) -> list[KnowledgeItem]:
        return [KnowledgeItem("k-1", "결제 타임아웃 근본원인", ("evt-1",))]


async def test_impact_uses_graph_and_accumulates_knowledge() -> None:
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)

    graph = GraphService(InMemoryGraphRepository(), bus)
    await bus.publish(Event("CommitsLinked", _Linked("i-1", "DIP-1", "c-1", "a1b2c3d")))

    builder = ContextBuilder(_OneItemSource())
    runner = WorkflowRunner(InMemoryAuditLog())
    agent = ImpactAgent(
        FakeLLMClient(response='{"summary":"결제 경로 영향","confidence":0.8}'),
        FilePromptRegistry(),
    )
    pipeline = ImpactPipeline(builder, runner, agent, GraphImpactSource(graph), bus)

    repo = InMemoryKnowledgeRepository()
    AgentKnowledgeRecorder(PromotionService(InMemoryIssueSourceReader(), repo, bus), bus)

    result = await pipeline.run("i-1")

    assert result.output["summary"] == "결제 경로 영향"
    assert result.confidence == 0.8

    impact_events = [
        event for event in store.events if event.name == IMPACT_ANALYZED
    ]
    assert len(impact_events) == 1
    payload = impact_events[0].payload
    assert isinstance(payload, ImpactAnalyzedPayload)
    assert payload.impacted_shas == ("a1b2c3d",)  # 그래프에서 산출한 사실

    knowledge = await repo.list_by_issue("i-1")
    assert any(item.type == "impact" for item in knowledge)
