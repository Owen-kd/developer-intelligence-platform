"""Postgres 조립 루트 (apps = composition root).

인메모리 [composition.py](composition.py) 와 같은 파이프라인을 **영속 어댑터**로 조립한다:
- 저장소: Postgres(issues/comments/commits/knowledge/events) — 재시작해도 데이터 유지.
- LLM: `ANTHROPIC_API_KEY` 가 있으면 실 `AnthropicClient`, 없으면 결정적 `FakeLLMClient`([ADR-006]).
- 수집원(Jira/Git)은 아직 Fake — 실 어댑터는 Sprint-14 ②/③([APR-002]).
- 그래프/인시던트는 in-memory 유지(Neo4j·인시던트 테이블은 Sprint-14 non-goal).

포트 뒤 어댑터만 교체하므로 platform/modules 코드는 변경되지 않는다(포트-어댑터).

실행 전제: `docker compose up -d` → `python -m apps.cli.migrate` (스키마 적용).
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.composition import _impact_response, _triage_response
from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import ContextBuilder
from dip_platform.event import InMemoryEventBus
from dip_platform.registry import FilePromptRegistry
from dip_platform.workflow import WorkflowRunner
from dip_platform.workflow.agents.impact import ImpactAgent, ImpactPipeline
from dip_platform.workflow.agents.triage import TriageAgent, TriagePipeline
from infrastructure.anthropic.client import AnthropicClient
from infrastructure.git.client import FakeGitClient
from infrastructure.jira.client import FakeJiraClient, HttpJiraClient, JiraClient
from infrastructure.llm.client import FakeLLMClient, LLMClient
from infrastructure.postgres.event_store import PostgresEventStore
from modules.git.application.service import GitService
from modules.git.infrastructure.repository import PostgresCommitRepository
from modules.graph.application.service import GraphService
from modules.graph.infrastructure.impact_source import GraphImpactSource
from modules.graph.infrastructure.repository import InMemoryGraphRepository
from modules.incident.application.service import IncidentPromotionService
from modules.incident.domain.entity import KnowledgeRef
from modules.incident.domain.repository import KnowledgeReader
from modules.incident.infrastructure.repository import InMemoryIncidentRepository
from modules.jira.application.service import JiraService
from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.recorder import AgentKnowledgeRecorder
from modules.knowledge.application.service import PromotionService
from modules.knowledge.domain.repository import KnowledgeRepository
from modules.knowledge.infrastructure.context_source import KnowledgeRepositorySource
from modules.knowledge.infrastructure.repository import (
    PostgresIssueSourceReader,
    PostgresKnowledgeRepository,
)
from shared.config.settings import Settings, get_settings


def _build_llm(settings: Settings) -> tuple[LLMClient, LLMClient]:
    """(triage, impact) LLM 어댑터를 만든다.

    키가 있으면 실 Anthropic(단일 클라이언트 공유), 없으면 데모용 결정적 Fake.
    """
    if settings.anthropic_api_key:
        client = AnthropicClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.llm_max_tokens,
        )
        return client, client
    return (
        FakeLLMClient(responder=_triage_response),
        FakeLLMClient(responder=_impact_response),
    )


def _build_jira(settings: Settings) -> tuple[JiraClient, str]:
    """(Jira 클라이언트, 모드) — 설정이 있으면 실 HTTP, 없으면 Fake."""
    if settings.jira_configured:
        client = HttpJiraClient(
            base_url=settings.jira_base_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key,
            max_issues=settings.jira_max_issues,
        )
        return client, "http"
    return FakeJiraClient(), "fake"


class _KnowledgeReaderAdapter(KnowledgeReader):
    """Knowledge 저장소를 incident 의 KnowledgeReader 포트로 노출한다(조립 계층)."""

    def __init__(self, repo: KnowledgeRepository) -> None:
        self._repo = repo

    async def refs_by_issue(self, issue_id: str) -> list[KnowledgeRef]:
        items = await self._repo.list_by_issue(issue_id)
        return [KnowledgeRef(id=item.id, type=item.type, summary=item.summary) for item in items]


@dataclass
class DipPostgresApp:
    """실행 완료된 Postgres 애플리케이션 — 읽기용 저장소 노출."""

    issue_repo: PostgresIssueRepository
    knowledge_repo: PostgresKnowledgeRepository
    incident_repo: InMemoryIncidentRepository
    audit: InMemoryAuditLog
    llm_mode: str  # "anthropic" | "fake"
    jira_mode: str  # "http" | "fake"


async def build_and_run_pg() -> DipPostgresApp:
    settings = get_settings()

    store = PostgresEventStore()
    bus = InMemoryEventBus(store=store)  # 발행 시 events 테이블에 append-only 적재
    audit = InMemoryAuditLog()

    issue_repo = PostgresIssueRepository()
    jira_client, jira_mode = _build_jira(settings)
    jira = JiraService(jira_client, issue_repo, bus)

    commit_repo = PostgresCommitRepository()
    git = GitService(FakeGitClient(), commit_repo, bus)  # subscribes IssueCreated
    graph = GraphService(InMemoryGraphRepository(), bus)  # subscribes CommitsLinked

    reader = PostgresIssueSourceReader()  # DB 조인으로 스냅샷(+출처 event ids) 조립
    knowledge_repo = PostgresKnowledgeRepository()
    promotion = PromotionService(reader, knowledge_repo, bus)
    AgentKnowledgeRecorder(promotion, bus)  # subscribes agent result events

    incident_repo = InMemoryIncidentRepository()
    incident = IncidentPromotionService(_KnowledgeReaderAdapter(knowledge_repo), incident_repo, bus)

    triage_llm, impact_llm = _build_llm(settings)
    llm_mode = "anthropic" if settings.anthropic_api_key else "fake"

    registry = FilePromptRegistry()
    runner = WorkflowRunner(audit)
    builder = ContextBuilder(KnowledgeRepositorySource(knowledge_repo))
    triage = TriagePipeline(builder, runner, TriageAgent(triage_llm, registry), bus)
    impact = ImpactPipeline(
        builder, runner, ImpactAgent(impact_llm, registry), GraphImpactSource(graph), bus
    )

    # 1) 수집 → 이벤트/원천 데이터가 Postgres 에 적재됨
    await jira.sync()
    await git.sync()

    # 2) 이슈별 승격 + Agent 실행 (스냅샷은 Postgres 리더가 DB 에서 조립)
    for issue in await issue_repo.list_issues():
        if issue.id is None:
            continue
        await promotion.promote_issue(issue.id)  # 원천 → Knowledge
        await triage.run(issue.id)  # 분류 → Knowledge
        await impact.run(issue.id)  # 영향도 → Knowledge
        await incident.promote(issue.id)  # Knowledge → Incident Library

    return DipPostgresApp(
        issue_repo=issue_repo,
        knowledge_repo=knowledge_repo,
        incident_repo=incident_repo,
        audit=audit,
        llm_mode=llm_mode,
        jira_mode=jira_mode,
    )
