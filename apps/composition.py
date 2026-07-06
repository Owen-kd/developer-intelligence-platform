"""In-memory 조립 루트 (apps = composition root).

전체 파이프라인을 fixture/인메모리 어댑터로 조립하고 1회 실행한다:
수집(jira/git) → 그래프 → Knowledge 승격 → Triage/Impact Agent → Knowledge 축적.
API/CLI/e2e 데모가 공유한다. 외부 자격증명·실 LLM 불필요([APR-002]/[APR-005]).
"""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import ContextBuilder
from dip_platform.event import InMemoryEventBus, InMemoryEventStore
from dip_platform.registry import FilePromptRegistry
from dip_platform.workflow import WorkflowRunner
from dip_platform.workflow.agents.impact import ImpactAgent, ImpactPipeline
from dip_platform.workflow.agents.triage import TriageAgent, TriagePipeline
from infrastructure.git.client import FakeGitClient
from infrastructure.jira.client import FakeJiraClient
from infrastructure.llm.client import FakeLLMClient
from modules.git.application.service import GitService
from modules.git.infrastructure.repository import InMemoryCommitRepository
from modules.graph.application.service import GraphService
from modules.graph.infrastructure.impact_source import GraphImpactSource
from modules.graph.infrastructure.repository import InMemoryGraphRepository
from modules.incident.application.service import IncidentPromotionService
from modules.incident.domain.entity import KnowledgeRef
from modules.incident.domain.repository import KnowledgeReader
from modules.incident.infrastructure.repository import InMemoryIncidentRepository
from modules.jira.application.service import JiraService
from modules.jira.infrastructure.repository import InMemoryIssueRepository
from modules.knowledge.application.recorder import AgentKnowledgeRecorder
from modules.knowledge.application.service import PromotionService
from modules.knowledge.domain.entity import IssueSnapshot
from modules.knowledge.infrastructure.context_source import KnowledgeRepositorySource
from modules.knowledge.infrastructure.repository import (
    InMemoryIssueSourceReader,
    InMemoryKnowledgeRepository,
)


def _triage_response(system: str, user: str) -> str:
    priority = "high" if "타임아웃" in user or "고갈" in user else "medium"
    category = "bug" if "타임아웃" in user or "고갈" in user else "question"
    return (
        f'{{"category":"{category}","priority":"{priority}",'
        f'"confidence":0.85,"rationale":"Context 근거 기반 분류"}}'
    )


def _impact_response(system: str, user: str) -> str:
    return '{"summary":"결제 경로와 연결 풀 관련 코드에 영향","confidence":0.8}'


class _KnowledgeReaderAdapter(KnowledgeReader):
    """knowledge 저장소를 incident 의 KnowledgeReader 포트로 노출한다(조립 계층)."""

    def __init__(self, repo: InMemoryKnowledgeRepository) -> None:
        self._repo = repo

    async def refs_by_issue(self, issue_id: str) -> list[KnowledgeRef]:
        items = await self._repo.list_by_issue(issue_id)
        return [KnowledgeRef(id=item.id, type=item.type, summary=item.summary) for item in items]


@dataclass
class DipInMemoryApp:
    """실행 완료된 인메모리 애플리케이션 — 읽기용 저장소 노출."""

    issue_repo: InMemoryIssueRepository
    knowledge_repo: InMemoryKnowledgeRepository
    incident_repo: InMemoryIncidentRepository
    store: InMemoryEventStore
    audit: InMemoryAuditLog


async def build_and_run() -> DipInMemoryApp:
    store = InMemoryEventStore()
    bus = InMemoryEventBus(store=store)
    audit = InMemoryAuditLog()

    issue_repo = InMemoryIssueRepository()
    jira = JiraService(FakeJiraClient(), issue_repo, bus)

    git = GitService(FakeGitClient(), InMemoryCommitRepository(), bus)  # subscribes IssueCreated
    graph = GraphService(InMemoryGraphRepository(), bus)  # subscribes CommitsLinked

    reader = InMemoryIssueSourceReader()
    knowledge_repo = InMemoryKnowledgeRepository()
    promotion = PromotionService(reader, knowledge_repo, bus)
    AgentKnowledgeRecorder(promotion, bus)  # subscribes agent result events

    incident_repo = InMemoryIncidentRepository()
    incident = IncidentPromotionService(_KnowledgeReaderAdapter(knowledge_repo), incident_repo, bus)

    registry = FilePromptRegistry()
    runner = WorkflowRunner(audit)
    builder = ContextBuilder(KnowledgeRepositorySource(knowledge_repo))
    triage = TriagePipeline(
        builder, runner, TriageAgent(FakeLLMClient(responder=_triage_response), registry), bus
    )
    impact = ImpactPipeline(
        builder,
        runner,
        ImpactAgent(FakeLLMClient(responder=_impact_response), registry),
        GraphImpactSource(graph),
        bus,
    )

    # 1) 수집
    await jira.sync()
    await git.sync()

    # 2) 이슈별 승격 + Agent 실행
    for issue in await issue_repo.list_issues():
        if issue.id is None:
            continue
        shas = await graph.impacted_commit_shas(issue.id)
        source_ids = tuple(
            event.event_id
            for event in store.events
            if getattr(event.payload, "issue_id", None) == issue.id
        )
        reader.add(
            IssueSnapshot(
                issue_id=issue.id,
                jira_key=issue.jira_key,
                summary=issue.summary,
                status=issue.status,
                priority=issue.priority,
                comments=tuple(comment.body for comment in issue.comments),
                commit_shas=tuple(shas),
                source_event_ids=source_ids,
            )
        )
        await promotion.promote_issue(issue.id)  # 원천 → Knowledge
        await triage.run(issue.id)  # 분류 → Knowledge
        await impact.run(issue.id)  # 영향도 → Knowledge
        await incident.promote(issue.id)  # Knowledge → Incident Library(승격 2)

    return DipInMemoryApp(
        issue_repo=issue_repo,
        knowledge_repo=knowledge_repo,
        incident_repo=incident_repo,
        store=store,
        audit=audit,
    )
