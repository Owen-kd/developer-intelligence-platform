"""Postgres 조립 루트 (apps = composition root).

인메모리 [composition.py](composition.py) 와 같은 파이프라인을 **영속 어댑터**로 조립한다:
- 저장소: Postgres(issues/comments/commits/knowledge/events) — 재시작해도 데이터 유지.
- LLM: `ANTHROPIC_API_KEY` 가 있으면 실 `AnthropicClient`, 없으면 결정적 `FakeLLMClient`([ADR-006]).
- 수집원(Jira/Git): `.env` 설정이 있으면 실 어댑터(HttpJiraClient/LocalGitClient), 없으면 Fake 폴백.
  현 환경은 설정됨 → 실 수집 동작(거버넌스 승인 [APR-002] 는 별개로 Pending).
- 그래프/인시던트는 in-memory 유지(Neo4j·인시던트 테이블은 Sprint-14 non-goal).

포트 뒤 어댑터만 교체하므로 platform/modules 코드는 변경되지 않는다(포트-어댑터).

실행 전제: `docker compose up -d` → `python -m apps.cli.migrate` (스키마 적용).
"""

from __future__ import annotations

from dataclasses import dataclass

from apps.composition import _impact_response, _triage_response
from dip_platform.audit import InMemoryAuditLog
from dip_platform.context import ContextBuilder
from dip_platform.event import Event, InMemoryEventBus
from dip_platform.registry import FilePromptRegistry
from dip_platform.workflow import WorkflowRunner
from dip_platform.workflow.agents.impact import ImpactAgent, ImpactPipeline
from dip_platform.workflow.agents.triage import TriageAgent, TriagePipeline
from infrastructure.anthropic.client import AnthropicClient
from infrastructure.git.client import (
    FakeGitClient,
    GitClient,
    LocalGitClient,
    MultiRepoGitClient,
)
from infrastructure.jira.client import FakeJiraClient, HttpJiraClient, JiraClient
from infrastructure.knowledgedocs.reader import read_docs
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
from modules.jira.domain.events import ISSUE_CREATED
from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.recorder import AgentKnowledgeRecorder
from modules.knowledge.application.service import PromotionService
from modules.knowledge.domain.entity import Knowledge
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


def _build_git(settings: Settings) -> tuple[GitClient, str]:
    """(Git 클라이언트, 모드) — 로컬 repo 경로들이 있으면 실 git log(멀티 repo), 없으면 Fake."""
    paths = settings.git_repo_list
    if not paths:
        return FakeGitClient(), "fake"
    clients: list[GitClient] = [LocalGitClient(p, settings.git_max_commits) for p in paths]
    client = clients[0] if len(clients) == 1 else MultiRepoGitClient(clients)
    return client, f"local×{len(paths)}"


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


async def ingest_knowledge_docs(directory: str = "knowledge") -> int:
    """`knowledge/*.md`(전문가 작성)를 verified Knowledge 로 흡수한다(멱등).

    자동 추출(derived)과 달리 신뢰등급 'verified' — 검색/답변 시 우선한다.
    """
    repo = PostgresKnowledgeRepository()
    docs = read_docs(directory)
    for doc in docs:
        await repo.save(
            Knowledge(
                id=doc.doc_id,
                type=doc.type,
                issue_id="",  # 전문가 문서는 특정 이슈에 매이지 않음
                summary=doc.title,
                body={
                    "content": doc.content,
                    "code_refs": doc.code_refs,
                    "issues": list(doc.issues),
                },
                sources=(f"doc:{doc.filename}",),
                source="verified",
            )
        )
    return len(docs)


@dataclass
class CollectResult:
    """수집+정제 1회 결과 요약 (LLM 미사용)."""

    jira_mode: str
    git_mode: str
    issues_synced: int
    issues_created: int
    commits_synced: int
    links_created: int  # 이슈↔커밋 신규 링크 수
    refined: int  # 이번에 정제(issue_summary 승격)한 신규 이슈 수
    verified_docs: int  # 흡수한 전문가 문서 수
    total_in_db: int


async def collect_and_refine() -> CollectResult:
    """수집 + 저비용 정제만 수행한다(LLM 0). 판단(triage/impact)은 분리된 단계.

    - 실 Jira 수집(페이지네이션) → Postgres 멱등 upsert + Event 적재.
    - 신규 이슈만 `issue_summary` 로 승격(재실행 시 중복 정제 없음).
    수집(대량/저렴)과 LLM 판단(선별/고비용)을 분리해 스케일에서 낭비를 없앤다.
    """
    settings = get_settings()

    store = PostgresEventStore()
    bus = InMemoryEventBus(store=store)

    issue_repo = PostgresIssueRepository()
    jira_client, jira_mode = _build_jira(settings)
    jira = JiraService(jira_client, issue_repo, bus)

    commit_repo = PostgresCommitRepository()
    git_client, git_mode = _build_git(settings)
    git = GitService(git_client, commit_repo, bus)  # IssueCreated 구독으로 jira_key→id 학습

    reader = PostgresIssueSourceReader()
    knowledge_repo = PostgresKnowledgeRepository()
    promotion = PromotionService(reader, knowledge_repo, bus)

    new_ids: list[str] = []

    async def _capture_new(event: Event) -> None:
        issue_id = getattr(event.payload, "issue_id", None)
        if issue_id is not None:
            new_ids.append(str(issue_id))

    bus.subscribe(ISSUE_CREATED, _capture_new)  # 신규 이슈만 정제 대상으로 수집

    sync = await jira.sync()  # 이슈/코멘트 수집 → 신규 IssueCreated 발행
    git_sync = await git.sync()  # 커밋 수집 + 이슈키 파싱 → issues 테이블 조회로 링크
    for issue_id in new_ids:
        await promotion.promote_issue(issue_id)  # 원천 → Knowledge(issue_summary), LLM 없음

    verified_docs = await ingest_knowledge_docs()  # 전문가 문서(knowledge/*.md) 흡수

    total = len(await issue_repo.list_issues())
    return CollectResult(
        jira_mode=jira_mode,
        git_mode=git_mode,
        issues_synced=sync.issues_synced,
        issues_created=sync.issues_created,
        commits_synced=git_sync.commits_synced,
        links_created=git_sync.links_created,
        refined=len(new_ids),
        verified_docs=verified_docs,
        total_in_db=total,
    )
