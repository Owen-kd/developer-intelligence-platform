"""위키·RAG 파이프라인 조립 (apps = composition root) — ADR-009.

두 가지 유스케이스를 배선한다(포트 뒤 어댑터만 조립, 모듈 코드 불변):
- `build_wikis`: (도메인 필터된) 이슈 → LLM 위키 생성 → 로컬 임베딩 → pgvector 적재.
- `ask`: 질문 → 질의 임베딩 → 코사인 top-k 위키 → (LLM) 답변 조립.

LLM/임베더는 설정으로 실/Fake 를 고른다:
- LLM: `ANTHROPIC_API_KEY` 있으면 실 Anthropic, 없으면 결정적 Fake(위키 JSON 생성).
- 임베더: 기본 로컬 fastembed. 테스트/오프라인은 `FakeEmbedder` 를 주입.

실행 전제: `docker compose up -d` → `python -m apps.cli.migrate`(009 포함).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import text

from dip_platform.event import Event, EventBus, InMemoryEventBus
from dip_platform.registry import FilePromptRegistry
from infrastructure.embedding.client import Embedder, FastEmbedEmbedder
from infrastructure.jira.client import FakeJiraClient, HttpJiraClient, JiraClient
from infrastructure.llm.client import FakeLLMClient, LLMClient
from infrastructure.postgres import connection as pg
from infrastructure.postgres.event_store import PostgresEventStore
from modules.jira.application.service import JiraService, SyncResult
from modules.jira.domain.events import ISSUE_CREATED
from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.refinement import assess
from modules.knowledge.application.wiki_service import (
    WIKI_TYPE,
    WikiGenerationService,
    wiki_embedding_text,
)
from modules.knowledge.domain.entity import Knowledge
from modules.knowledge.domain.repository import IssueSourceReader, KnowledgeRepository
from modules.knowledge.infrastructure.repository import (
    PostgresIssueSourceReader as _SnapshotReader,
)
from modules.knowledge.infrastructure.repository import PostgresKnowledgeRepository
from shared.config.settings import Settings, get_settings
from shared.logger import get_logger

_logger = get_logger("apps.wiki")

# 상품 도메인 서가(components) 매칭 키워드 — 이 첫 범위(오너 지시).
PRODUCT_KEYWORDS = ("상품", "쿠팡")

# 이 유사도 미만이면 "제대로 못 답함"으로 보고 gap 로그에 남긴다(되먹임 씨앗).
# e5 코사인 분포 라이브 관측 보정: 무관 ~0.79, 관련 ~0.88+ → 0.82 로 분리.
GAP_SCORE_THRESHOLD = 0.82


def is_gap(hits: list[tuple[Knowledge, float]], threshold: float = GAP_SCORE_THRESHOLD) -> bool:
    """검색 결과가 없거나 최상위 유사도가 임계 미만이면 '지식 구멍'으로 판정(순수 함수)."""
    return not hits or hits[0][1] < threshold


async def _record_gap(question: str, hits: list[tuple[Knowledge, float]]) -> None:
    top = hits[0][1] if hits else 0.0
    sql = text(
        "INSERT INTO query_gaps (question, hit_count, top_score) VALUES (:q, :n, :s)"
    )
    async with pg.get_engine().begin() as conn:
        await conn.execute(sql, {"q": question, "n": len(hits), "s": top})


def _fake_wiki_response(_system: str, user: str) -> str:
    """키 없이도 파이프라인이 돌도록 최소 유효 위키 JSON 을 만든다(결정적).

    실제 근본원인 추론은 못 하지만, 저장/임베딩/검색 배선 검증엔 충분하다.
    """
    title = "무제 위키"
    for line in user.splitlines():
        if line.startswith("제목:"):
            title = line.removeprefix("제목:").strip() or title
            break
    payload = {
        "title": title,
        "symptom": "(fake) 이슈 본문 기반 증상 요약",
        "root_cause": "확인 필요: fake 모드 — 실제 근본원인 분석은 실 LLM 필요",
        "resolution": "(fake) 조치 요약",
        "code_refs": "",
        "related_issues": [],
        "content": f"## 개요\n{title}\n\n## 근본원인\n확인 필요(fake 모드).",
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_llm(settings: Settings) -> tuple[LLMClient, str]:
    if settings.anthropic_api_key:
        from infrastructure.anthropic.client import AnthropicClient

        client = AnthropicClient(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=max(settings.llm_max_tokens, 4096),  # 위키 본문(마크다운)은 길다 — 잘림 방지
        )
        return client, "anthropic"
    return FakeLLMClient(responder=_fake_wiki_response), "fake"


def _build_embedder(settings: Settings) -> Embedder:
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim)


@dataclass
class BuildResult:
    llm_mode: str
    candidates: int  # 도메인 필터를 통과한 이슈 수
    wikis_built: int  # 실제 생성·임베딩한 위키 수
    failed: int  # 생성/검증 실패로 건너뛴 이슈 수(정직 보고 — 배치는 1건 실패로 멈추지 않는다)
    index_only: int  # 가치 게이트 탈락(제목+상태만) — LLM 비용 절약분


@dataclass
class AskResult:
    question: str
    answer: str
    hits: list[tuple[Knowledge, float]]  # (위키, 유사도) 내림차순


async def _product_issue_ids(keywords: tuple[str, ...]) -> list[str]:
    """components(서가)에 키워드가 포함된 이슈 id 를 반환한다(상품 도메인 필터)."""
    patterns = [f"%{keyword}%" for keyword in keywords]
    query = text(
        """
        SELECT i.id::text AS id FROM issues i
        WHERE EXISTS (
            SELECT 1 FROM jsonb_array_elements_text(i.components) c
            WHERE c ILIKE ANY(:pats)
        )
        ORDER BY i.updated_at DESC
        """
    )
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(query, {"pats": patterns})).all()
    return [row.id for row in rows]


async def _grounding_for(keywords: tuple[str, ...], limit: int = 3) -> tuple[Knowledge, ...]:
    """이슈 키워드와 겹치는 검증(verified) 지식을 근거로 뽑는다(없으면 빈 튜플)."""
    patterns = [f"%{keyword}%" for keyword in keywords if keyword.strip()]
    if not patterns:
        return ()
    query = text(
        """
        SELECT id, type, issue_id, summary, body, sources, source, created_at
        FROM knowledge
        WHERE source = 'verified'
          AND (summary || ' ' || coalesce(body->>'content','')) ILIKE ANY(:pats)
        ORDER BY created_at DESC LIMIT :lim
        """
    )
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(query, {"pats": patterns, "lim": limit})).all()
    return tuple(
        Knowledge(
            id=str(row.id),
            type=row.type,
            issue_id=str(row.issue_id) if row.issue_id else "",
            summary=row.summary,
            body=row.body,
            sources=tuple(row.sources),
            source=row.source,
            created_at=row.created_at,
        )
        for row in rows
    )


async def build_wikis(
    *,
    keywords: tuple[str, ...] = PRODUCT_KEYWORDS,
    limit: int | None = None,
    embedder: Embedder | None = None,
    llm: LLMClient | None = None,
) -> BuildResult:
    """도메인 이슈들을 위키로 생성·임베딩·적재한다(멱등)."""
    settings = get_settings()
    if llm is not None:
        llm_mode = "injected"
    else:
        llm, llm_mode = _build_llm(settings)
    embedder = embedder or _build_embedder(settings)
    reader = _SnapshotReader()
    knowledge_repo = PostgresKnowledgeRepository()
    service = WikiGenerationService(llm, FilePromptRegistry(), knowledge_repo)

    issue_ids = await _product_issue_ids(keywords)
    if limit is not None:
        issue_ids = issue_ids[:limit]

    built = 0
    failed = 0
    index_only = 0
    for issue_id in issue_ids:
        snapshot = await reader.get_snapshot(issue_id)
        if snapshot is None:
            continue
        # 가치 게이트: 신호 빈약한 이슈는 LLM 생성 스킵(제목+상태만 인덱싱) — 비용 절약
        refinement = assess(
            snapshot.comments,
            description=snapshot.description,
            commit_shas=snapshot.commit_shas,
        )
        if not refinement.worthy:
            index_only += 1
            _logger.info("wiki.index_only", jira_key=snapshot.jira_key)
            continue
        try:
            grounding = await _grounding_for(snapshot.components or keywords)
            wiki = await service.generate(snapshot, grounding)
            vectors = await embedder.embed_documents([wiki_embedding_text(wiki)])
            await knowledge_repo.save_embedding(wiki.id, vectors[0])
        except Exception as exc:  # 배치는 1건 실패(예: LLM 출력 검증 실패)로 멈추지 않는다
            failed += 1
            _logger.warning("wiki.failed", jira_key=snapshot.jira_key, error=str(exc))
            continue
        built += 1
        _logger.info("wiki.built", jira_key=snapshot.jira_key, grounded=len(grounding))

    return BuildResult(
        llm_mode=llm_mode,
        candidates=len(issue_ids),
        wikis_built=built,
        failed=failed,
        index_only=index_only,
    )


def _in_domain(components: tuple[str, ...], keywords: tuple[str, ...]) -> bool:
    """서가(components)에 도메인 키워드가 하나라도 포함되면 True."""
    return any(keyword in component for component in components for keyword in keywords)


class WikiAutoGenerator:
    """루프2 자동화: IssueCreated 이벤트 → (도메인 필터 통과 시) 위키 생성·임베딩.

    수집(루프1)이 새 이슈를 발행하면 사람 개입 없이 지식화된다([target-service] 루프2).
    한 건 실패가 다른 건을 막지 않는다(배치 견고성). 멱등 — 같은 이슈는 재생성해도 같은 행.
    """

    def __init__(
        self,
        service: WikiGenerationService,
        reader: IssueSourceReader,
        repo: KnowledgeRepository,
        embedder: Embedder,
        bus: EventBus,
        keywords: tuple[str, ...] = PRODUCT_KEYWORDS,
    ) -> None:
        self._service = service
        self._reader = reader
        self._repo = repo
        self._embedder = embedder
        self._keywords = keywords
        self.generated = 0  # 관측용 카운터
        bus.subscribe(ISSUE_CREATED, self._on_issue_created)

    async def _on_issue_created(self, event: Event) -> None:
        issue_id = getattr(event.payload, "issue_id", None)
        if issue_id is None:
            return
        snapshot = await self._reader.get_snapshot(str(issue_id))
        if snapshot is None or not _in_domain(snapshot.components, self._keywords):
            return
        # 가치 게이트: 신호 빈약한 이슈는 자동 위키 생성 스킵(제목+상태만 인덱싱)
        if not assess(
            snapshot.comments,
            description=snapshot.description,
            commit_shas=snapshot.commit_shas,
        ).worthy:
            _logger.info("wiki.auto_index_only", jira_key=snapshot.jira_key)
            return
        try:
            wiki = await self._service.generate(snapshot)
            vectors = await self._embedder.embed_documents([wiki_embedding_text(wiki)])
            if hasattr(self._repo, "save_embedding"):
                await self._repo.save_embedding(wiki.id, vectors[0])
            self.generated += 1
            _logger.info("wiki.auto_generated", jira_key=snapshot.jira_key)
        except Exception as exc:  # 자동화는 1건 실패로 멈추지 않는다
            _logger.warning("wiki.auto_failed", jira_key=snapshot.jira_key, error=str(exc))


class _RelatedStore(Protocol):
    """루프3-Push 가 필요로 하는 저장소 능력(구조적 타이핑)."""

    async def search_semantic(
        self, embedding: list[float], limit: int = 5, types: tuple[str, ...] = ()
    ) -> list[tuple[Knowledge, float]]: ...

    async def link_related_wiki(self, issue_id: str, wiki_id: str, score: float) -> None: ...


class RelatedKnowledgePush:
    """루프3-Push: IssueCreated → 유사 과거 위키 top-k 를 이슈에 관련지식으로 연결.

    이슈 본문을 질의로 임베딩해 다른 이슈의 위키를 찾는다(자기 자신 제외). 팀 간 지식 격차 해소.
    내부 저장만 — 실 Jira 코멘트 쓰기는 별도 승인 게이트([target-service] #5).
    """

    def __init__(
        self,
        reader: IssueSourceReader,
        store: _RelatedStore,
        embedder: Embedder,
        bus: EventBus,
        k: int = 3,
        keywords: tuple[str, ...] = PRODUCT_KEYWORDS,
    ) -> None:
        self._reader = reader
        self._store = store
        self._embedder = embedder
        self._k = k
        self._keywords = keywords
        self.linked = 0
        bus.subscribe(ISSUE_CREATED, self._on_issue_created)

    async def _on_issue_created(self, event: Event) -> None:
        issue_id = getattr(event.payload, "issue_id", None)
        if issue_id is None:
            return
        snapshot = await self._reader.get_snapshot(str(issue_id))
        if snapshot is None or not _in_domain(snapshot.components, self._keywords):
            return
        try:
            query_text = f"{snapshot.summary}\n{snapshot.description}"
            vectors = await self._embedder.embed_query(query_text)
            hits = await self._store.search_semantic(
                vectors, limit=self._k + 1, types=(WIKI_TYPE,)
            )
            related = [(w, s) for w, s in hits if w.issue_id != str(issue_id)][: self._k]
            for wiki, score in related:
                await self._store.link_related_wiki(str(issue_id), wiki.id, score)
            self.linked += len(related)
            _logger.info("push.linked", jira_key=snapshot.jira_key, count=len(related))
        except Exception as exc:  # Push 실패가 다른 처리를 막지 않는다
            _logger.warning("push.failed", jira_key=snapshot.jira_key, error=str(exc))


def _build_jira_client(settings: Settings) -> tuple[JiraClient, str]:
    if settings.jira_configured:
        return (
            HttpJiraClient(
                base_url=settings.jira_base_url,
                email=settings.jira_email,
                api_token=settings.jira_api_token,
                project_key=settings.jira_project_key,
                max_issues=settings.jira_max_issues,
            ),
            "http",
        )
    return FakeJiraClient(), "fake"


@dataclass
class CollectGenerateResult:
    jira_mode: str
    issues_synced: int
    issues_created: int
    wikis_generated: int  # 신규 이슈 중 도메인 필터 통과분만 자동 위키화
    related_linked: int  # 신규 이슈에 자동 연결된 관련 위키 링크 수(루프3-Push)


async def collect_and_generate(
    *, embedder: Embedder | None = None, llm: LLMClient | None = None
) -> CollectGenerateResult:
    """루프1→루프2 자동 배선(1회): Jira 수집 → 신규 이슈 IssueCreated → 자동 위키 생성·임베딩.

    상시 서비스에선 이 조립을 worker 가 이벤트 브로커(Redis) 위에서 돌린다([target-service]).
    여기서는 in-process 이벤트로 자동화를 증명한다(신규 이슈 없으면 위키 0 — 비용 0).
    """
    settings = get_settings()
    store = PostgresEventStore()
    bus = InMemoryEventBus(store=store)

    issue_repo = PostgresIssueRepository()
    jira_client, jira_mode = _build_jira_client(settings)
    jira = JiraService(jira_client, issue_repo, bus)

    reader = _SnapshotReader()
    knowledge_repo = PostgresKnowledgeRepository()
    wiki_llm = llm if llm is not None else _build_llm(settings)[0]
    service = WikiGenerationService(wiki_llm, FilePromptRegistry(), knowledge_repo)
    embedder = embedder or _build_embedder(settings)
    auto = WikiAutoGenerator(service, reader, knowledge_repo, embedder, bus)  # 루프2
    push = RelatedKnowledgePush(reader, knowledge_repo, embedder, bus)  # 루프3-Push

    sync: SyncResult = await jira.sync()  # 신규 이슈 → IssueCreated → auto/push 구독 발화
    return CollectGenerateResult(
        jira_mode=jira_mode,
        issues_synced=sync.issues_synced,
        issues_created=sync.issues_created,
        wikis_generated=auto.generated,
        related_linked=push.linked,
    )


async def ask(
    question: str,
    k: int = 5,
    *,
    embedder: Embedder | None = None,
    llm: LLMClient | None = None,
    log_gap: bool = True,
) -> AskResult:
    """RAG: 질문과 유사한 위키를 찾아 LLM 답변을 조립한다(위키 없으면 검색 결과만).

    근거가 없거나 약하면(is_gap) 질문을 query_gaps 에 남긴다(되먹임). gap 실패는 답변을 막지 않는다.
    """
    settings = get_settings()
    embedder = embedder or _build_embedder(settings)
    knowledge_repo = PostgresKnowledgeRepository()

    query_vec = await embedder.embed_query(question)
    hits = await knowledge_repo.search_semantic(query_vec, limit=k, types=(WIKI_TYPE,))

    if log_gap and is_gap(hits):
        try:
            await _record_gap(question, hits)
        except Exception as exc:  # gap 로깅 실패가 답변을 막지 않는다
            _logger.warning("gap.log_failed", error=str(exc))

    if not hits:
        return AskResult(question=question, answer="도서관에 관련 위키가 없습니다.", hits=[])

    if llm is not None:
        llm_mode = "injected"
    else:
        llm, llm_mode = _build_llm(settings)
    if llm_mode == "fake":
        # 실 LLM 이 없으면 검색 결과만 돌려준다(임의 생성 금지).
        return AskResult(question=question, answer="(LLM 미설정 — 검색 결과만 표시)", hits=hits)

    system = FilePromptRegistry().get("knowledge/ask")
    context = "\n\n".join(
        f"[{_jira_of(k_item)}] {k_item.summary}\n{_body_content(k_item)}" for k_item, _ in hits
    )
    answer = await llm.complete(system, f"질문: {question}\n\n참고 위키:\n{context}")
    return AskResult(question=question, answer=answer, hits=hits)


def _jira_of(knowledge: Knowledge) -> str:
    for source in knowledge.sources:
        if source.startswith("issue:"):
            return source.removeprefix("issue:")
    return knowledge.issue_id or "-"


def _body_content(knowledge: Knowledge) -> str:
    return str(knowledge.body.get("content", "")) if isinstance(knowledge.body, dict) else ""
