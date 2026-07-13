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
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Protocol

from sqlalchemy import text

from dip_platform.event import Event, EventBus, InMemoryEventBus
from dip_platform.registry import FilePromptRegistry
from infrastructure.embedding.client import Embedder, get_embedder
from infrastructure.embedding.reranker import Reranker, get_reranker
from infrastructure.jira.client import FakeJiraClient, HttpJiraClient, JiraClient
from infrastructure.llm.client import FakeLLMClient, LLMClient
from infrastructure.postgres import connection as pg
from infrastructure.postgres.event_store import PostgresEventStore
from modules.jira.application.service import JiraService, SyncResult
from modules.jira.domain.events import ISSUE_CREATED
from modules.jira.infrastructure.repository import PostgresIssueRepository
from modules.knowledge.application.classification import classify_rule
from modules.knowledge.application.diversify import mmr_select
from modules.knowledge.application.fusion import hybrid_merge
from modules.knowledge.application.gap_analysis import GapRecord
from modules.knowledge.application.refinement import assess
from modules.knowledge.application.wiki_service import (
    WIKI_TYPE,
    WikiGenerationService,
    wiki_embedding_text,
)
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.events import ISSUE_CLASSIFIED, IssueClassifiedPayload
from modules.knowledge.domain.repository import IssueSourceReader
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


async def load_gap_records() -> list[GapRecord]:
    """query_gaps 전체를 읽어 집계 입력(GapRecord)으로 반환한다(되먹임)."""
    sql = text("SELECT question, hit_count, top_score FROM query_gaps")
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql)).all()
    return [
        GapRecord(question=row.question, hit_count=row.hit_count, top_score=row.top_score)
        for row in rows
    ]


async def gap_candidates(question: str, limit: int = 5) -> list[tuple[str, str]]:
    """gap 질문과 겹치지만 **아직 위키가 없는** 이슈를 찾는다(=위키화 후보).

    되먹임을 닫는 지점: "이 질문에 답할 이슈가 있는데 위키가 없다" → 생성 대상.
    """
    words = [word for word in question.split() if len(word) >= 2]
    if not words:
        return []
    patterns = [f"%{word}%" for word in words]
    sql = text(
        """
        SELECT i.jira_key, i.summary FROM issues i
        WHERE (i.summary || ' ' || coalesce(i.description,'')) ILIKE ANY(:pats)
          AND NOT EXISTS (
              SELECT 1 FROM knowledge k WHERE k.type = 'wiki' AND k.issue_id = i.id
          )
        ORDER BY i.updated_at DESC LIMIT :lim
        """
    )
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql, {"pats": patterns, "lim": limit})).all()
    return [(row.jira_key, row.summary) for row in rows]


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


def _build_wiki_llm(settings: Settings) -> tuple[LLMClient, str]:
    """위키 생성용 LLM — `wiki_model`(기본 Haiku, 저가). 비어있으면 anthropic_model 로 폴백."""
    if settings.anthropic_api_key:
        from infrastructure.anthropic.client import AnthropicClient

        model = settings.wiki_model or settings.anthropic_model
        client = AnthropicClient(
            api_key=settings.anthropic_api_key,
            model=model,
            max_tokens=max(settings.llm_max_tokens, 4096),
        )
        return client, model
    return FakeLLMClient(responder=_fake_wiki_response), "fake"


def _wiki_type_allowed(snapshot: IssueSnapshot, allowed: frozenset[str]) -> bool:
    """이슈 유형(facet)이 위키화 대상인지 — '문의' 등은 제외해 비용↓·지식품질↑ (규칙, 무료)."""
    if not allowed:
        return True
    facets = classify_rule(
        snapshot.components, snapshot.labels, snapshot.jira_key, snapshot.summary
    )
    return facets.issue_type in allowed


def _build_embedder(settings: Settings) -> Embedder:
    return get_embedder()  # 프로세스 단일 캐시 인스턴스(재생성 방지)


async def _maybe_export_obsidian(settings: Settings, generated: int) -> int:
    """위키가 생성됐고 auto_export 가 켜져 있으면 Obsidian 볼트를 갱신한다(비파괴). 내보낸 수."""
    if not settings.obsidian_auto_export or generated <= 0:
        return 0
    from apps.obsidian_export import export_vault

    try:
        result = await export_vault(settings.obsidian_vault_path)
        _logger.info("obsidian.auto_export", written=result.written)
        return result.written
    except Exception as exc:  # export 실패가 생성 파이프라인을 막지 않는다(파생 뷰)
        _logger.warning("obsidian.auto_export_failed", error=str(exc))
        return 0


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


async def _domain_issue_ids(
    domains: frozenset[str], only_missing: bool = False
) -> list[str]:
    """facet 도메인(issue_facets.domain)이 대상 도메인인 이슈 id 를 반환한다(위키화 후보).

    컴포넌트 키워드가 아니라 **분류된 도메인**으로 거른다(ADR-015) — 정확·설정으로 도메인 확장.
    `only_missing` 이면 아직 위키가 없는 이슈만(백필 대상).
    """
    if not domains:
        return []
    missing_cond = (
        "AND NOT EXISTS (SELECT 1 FROM knowledge k WHERE k.type='wiki' AND k.issue_id = i.id)"
        if only_missing
        else ""
    )
    query = text(
        f"""
        SELECT i.id::text AS id FROM issues i
        JOIN issue_facets f ON f.issue_id = i.id
        WHERE f.domain = ANY(:domains) {missing_cond}
        ORDER BY i.updated_at DESC
        """
    )
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(query, {"domains": list(domains)})).all()
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
    domains: frozenset[str] | None = None,
    limit: int | None = None,
    only_missing: bool = False,
    embedder: Embedder | None = None,
    llm: LLMClient | None = None,
) -> BuildResult:
    """대상 도메인 이슈들을 위키로 생성·임베딩·적재한다(멱등).

    `domains` 미지정 시 설정(wiki_domains, 기본 product+order). 유형 게이트(오류/기능개선) +
    가치 게이트로 비용 절감. `only_missing` 이면 아직 위키 없는 이슈만(백필). `limit` 로 배치 제한.
    """
    settings = get_settings()
    domains = domains if domains is not None else settings.wiki_domain_set
    if llm is not None:
        llm_mode = "injected"
    else:
        llm, llm_mode = _build_wiki_llm(settings)  # 기본 Haiku(저가)
    embedder = embedder or _build_embedder(settings)
    reader = _SnapshotReader()
    knowledge_repo = PostgresKnowledgeRepository()
    service = WikiGenerationService(llm, FilePromptRegistry(), knowledge_repo)
    wiki_types = settings.wiki_type_set

    issue_ids = await _domain_issue_ids(domains, only_missing=only_missing)
    if limit is not None:
        issue_ids = issue_ids[:limit]

    built = 0
    failed = 0
    index_only = 0
    for issue_id in issue_ids:
        snapshot = await reader.get_snapshot(issue_id)
        if snapshot is None:
            continue
        # 유형 게이트: 오류/기능개선만 위키화, 문의 등 스킵(비용↓·품질↑) — LLM 0
        if not _wiki_type_allowed(snapshot, wiki_types):
            index_only += 1
            _logger.info("wiki.skip_type", jira_key=snapshot.jira_key)
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
            grounding = await _grounding_for(snapshot.components or ())
            wiki = await service.generate(snapshot, grounding)
            vectors = await embedder.embed_documents([wiki_embedding_text(wiki)])
            await knowledge_repo.save_embedding(wiki.id, vectors[0])
        except Exception as exc:  # 배치는 1건 실패(예: LLM 출력 검증 실패)로 멈추지 않는다
            failed += 1
            _logger.warning("wiki.failed", jira_key=snapshot.jira_key, error=str(exc))
            continue
        built += 1
        _logger.info("wiki.built", jira_key=snapshot.jira_key, grounded=len(grounding))

    await _maybe_export_obsidian(settings, built)  # 배치 후 볼트 자동 갱신(ON 시)
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


class _EmbeddingSink(Protocol):
    """WikiAutoGenerator 가 필요로 하는 임베딩 저장 능력(구조적 타이핑)."""

    async def save_embedding(self, knowledge_id: str, embedding: list[float]) -> None: ...


class _FacetSink(Protocol):
    """IssueFacetClassifier 가 필요로 하는 facet 저장·조회 능력(구조적 타이핑)."""

    async def save_facets(
        self, issue_id: str, facets: dict[str, str], method: str = "rule"
    ) -> None: ...

    async def facets_exist(self, issue_id: str) -> bool: ...


class IssueFacetClassifier:
    """루프1 자동화: IssueCreated → 규칙 facet 분류 → issue_facets 저장 → IssueClassified 발행.

    규칙만(LLM 0 · 즉시 · 무료). 규칙이 미상인 축은 주기 배치(`classify enrich`)가 보강한다.
    멱등 — 같은 이슈 재분류는 upsert. 한 건 실패가 다른 건을 막지 않는다.
    """

    def __init__(self, reader: IssueSourceReader, sink: _FacetSink, bus: EventBus) -> None:
        self._reader = reader
        self._sink = sink
        self._bus = bus
        self.classified = 0  # 관측용 카운터
        bus.subscribe(ISSUE_CREATED, self._on_issue_created)

    async def _on_issue_created(self, event: Event) -> None:
        issue_id = getattr(event.payload, "issue_id", None)
        if issue_id is None:
            return
        # 멱등·비파괴: 이미 분류된 이슈는 스킵한다. IssueCreated 는 신규 이슈에만 발화하지만,
        # at-least-once 재전송(Redis) 시 규칙 재분류가 기존 LLM 보강(method='llm')을 덮지 않도록.
        if await self._sink.facets_exist(str(issue_id)):
            return
        snapshot = await self._reader.get_snapshot(str(issue_id))
        if snapshot is None:
            return
        facets = classify_rule(
            snapshot.components, snapshot.labels, snapshot.jira_key, snapshot.summary
        )
        await self._sink.save_facets(str(issue_id), asdict(facets), method="rule")
        self.classified += 1
        await self._bus.publish(
            Event(
                ISSUE_CLASSIFIED,
                IssueClassifiedPayload(
                    str(issue_id), snapshot.jira_key, facets.domain, facets.channel, "rule"
                ),
            )
        )


class WikiAutoGenerator:
    """루프2 자동화: IssueCreated 이벤트 → (도메인 필터 통과 시) 위키 생성·임베딩.

    수집(루프1)이 새 이슈를 발행하면 사람 개입 없이 지식화된다([target-service] 루프2).
    한 건 실패가 다른 건을 막지 않는다(배치 견고성). 멱등 — 같은 이슈는 재생성해도 같은 행.
    """

    def __init__(
        self,
        service: WikiGenerationService,
        reader: IssueSourceReader,
        repo: _EmbeddingSink,
        embedder: Embedder,
        bus: EventBus,
        wiki_domains: frozenset[str] = frozenset(),
        wiki_types: frozenset[str] = frozenset(),
    ) -> None:
        self._service = service
        self._reader = reader
        self._repo = repo
        self._embedder = embedder
        self._wiki_domains = wiki_domains  # 이 도메인만 위키화(빈 set=제한 없음)
        self._wiki_types = wiki_types  # 이 유형만 위키화(빈 set=제한 없음). '문의' 등 비용 절감.
        self.generated = 0  # 관측용 카운터
        self.skipped_gate = 0  # 도메인/유형 게이트로 스킵된 수(관측)
        bus.subscribe(ISSUE_CREATED, self._on_issue_created)

    async def _on_issue_created(self, event: Event) -> None:
        issue_id = getattr(event.payload, "issue_id", None)
        if issue_id is None:
            return
        snapshot = await self._reader.get_snapshot(str(issue_id))
        if snapshot is None:
            return
        # 도메인/유형 게이트(facet, LLM 0): 대상 도메인 + 오류/기능개선만. 문의 등 스킵(비용↓).
        facets = classify_rule(
            snapshot.components, snapshot.labels, snapshot.jira_key, snapshot.summary
        )
        if self._wiki_domains and facets.domain not in self._wiki_domains:
            return
        if self._wiki_types and facets.issue_type not in self._wiki_types:
            self.skipped_gate += 1
            _logger.info("wiki.auto_skip_gate", jira_key=snapshot.jira_key)
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
    issues_classified: int = 0  # 신규 이슈 자동 facet 분류 수(ADR-015)
    wikis_generated: int = 0  # 신규 이슈 중 도메인 필터 통과분만 자동 위키화
    related_linked: int = 0  # 신규 이슈에 자동 연결된 관련 위키 링크 수(루프3-Push)
    obsidian_exported: int = 0  # Obsidian 볼트에 자동 export 된 위키 수(auto_export ON 시)


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
    wiki_llm = llm if llm is not None else _build_wiki_llm(settings)[0]  # 기본 Haiku(저가)
    service = WikiGenerationService(wiki_llm, FilePromptRegistry(), knowledge_repo)
    embedder = embedder or _build_embedder(settings)
    classifier = IssueFacetClassifier(reader, issue_repo, bus)  # 신규 이슈 자동 facet 분류
    auto = WikiAutoGenerator(  # 루프2: 도메인+유형 게이트(문의 스킵)로 비용↓
        service, reader, knowledge_repo, embedder, bus,
        wiki_domains=settings.wiki_domain_set, wiki_types=settings.wiki_type_set,
    )
    push = RelatedKnowledgePush(reader, knowledge_repo, embedder, bus)  # 루프3-Push

    sync: SyncResult = await jira.sync()  # 신규 이슈 → IssueCreated → classify/auto/push 구독 발화
    exported = await _maybe_export_obsidian(settings, auto.generated)  # 볼트 자동 갱신
    return CollectGenerateResult(
        jira_mode=jira_mode,
        issues_synced=sync.issues_synced,
        issues_created=sync.issues_created,
        issues_classified=classifier.classified,
        wikis_generated=auto.generated,
        related_linked=push.linked,
        obsidian_exported=exported,
    )


def _build_reranker(settings: Settings) -> Reranker | None:
    """설정이 켜져 있으면 프로세스 단일 리랭커, 꺼져 있으면 None(융합 순위 그대로)."""
    if not settings.rerank_enabled:
        return None
    return get_reranker()


async def apply_rerank(
    reranker: Reranker,
    query: str,
    hits: list[tuple[Knowledge, float]],
) -> list[tuple[Knowledge, float]]:
    """cross-encoder 로 후보를 재정렬한다. 반환 점수는 리랭커 관련도(융합 코사인 대체)."""
    if not hits:
        return hits
    docs = [wiki_embedding_text(k) for k, _ in hits]
    scores = await reranker.rerank(query, docs)
    ranked = sorted(zip(hits, scores, strict=True), key=lambda item: item[1], reverse=True)
    return [(k, float(score)) for (k, _cosine), score in ranked]


async def hybrid_search(
    question: str,
    embedder: Embedder,
    k: int,
    *,
    shelf_patterns: tuple[str, ...] = (),
    reranker: Reranker | None = None,
    diversify: bool | None = None,
    facet_filters: Mapping[str, str] | None = None,
) -> tuple[list[tuple[Knowledge, float]], list[tuple[Knowledge, float]]]:
    """벡터+전문검색 융합 → (선택)리랭커 재정렬 → (선택)MMR 다양화. (top-k, 벡터히트) 반환.

    벡터히트는 gap 판정(커버리지)용 — 리랭커/융합/다양화가 순위를 바꿔도 커버리지 신호는
    의미유사도(코사인) 원본을 쓴다. `diversify` 미지정 시 설정(diversify_enabled)을 따른다.
    `facet_filters`(ADR-015) 가 주어지면 그 축(도메인/채널/유형...)의 위키만 검색한다.
    """
    settings = get_settings()
    if diversify is None:
        diversify = settings.diversify_enabled
    knowledge_repo = PostgresKnowledgeRepository()
    query_vec = await embedder.embed_query(question)
    vector_hits = await knowledge_repo.search_semantic(
        query_vec, limit=30, types=(WIKI_TYPE,),
        shelf_patterns=shelf_patterns, facet_filters=facet_filters,
    )
    keyword_hits = await knowledge_repo.search_keyword(
        question, limit=30, types=(WIKI_TYPE,),
        shelf_patterns=shelf_patterns, facet_filters=facet_filters,
    )
    # 리랭커/다양화가 있으면 더 넓은 풀(rerank_pool)을 뽑아 후처리한 뒤 top-k 로 자른다.
    want_pool = reranker is not None or diversify
    pool = settings.rerank_pool if want_pool else k
    fused = hybrid_merge(vector_hits, keyword_hits, pool)
    if reranker is not None and fused:
        fused = await apply_rerank(reranker, question, fused)
    if diversify and len(fused) > k:
        embeddings = await knowledge_repo.embeddings_for([kn.id for kn, _ in fused])
        fused = mmr_select(fused, embeddings, k, settings.diversify_lambda)
    return fused[:k], vector_hits


async def ask(
    question: str,
    k: int = 5,
    *,
    embedder: Embedder | None = None,
    llm: LLMClient | None = None,
    reranker: Reranker | None = None,
    log_gap: bool = True,
    shelf_patterns: tuple[str, ...] = (),
    facet_filters: Mapping[str, str] | None = None,
) -> AskResult:
    """RAG: 질문과 유사한 위키를 찾아 LLM 답변을 조립한다(위키 없으면 검색 결과만).

    근거가 없거나 약하면(is_gap) 질문을 query_gaps 에 남긴다(되먹임). gap 실패는 답변을 막지 않는다.
    `shelf_patterns`(접근제어, ADR-010) 가 주어지면 그 서가의 위키만 검색한다.
    `facet_filters`(ADR-015) 가 주어지면 그 축(도메인/채널/유형...)으로 좁혀 검색한다.
    """
    settings = get_settings()
    embedder = embedder or _build_embedder(settings)
    reranker = reranker if reranker is not None else _build_reranker(settings)

    # 접근제어로 서가 필터된 질의는 gap 신호를 오염시키지 않는다: "다른 팀 서가라 안 보임"과
    # "지식이 없음"을 구분할 수 없고, 제한된 사용자의 질문 원문을 gap 로그에 남기지 않기 위함.
    if shelf_patterns or facet_filters:
        log_gap = False

    # 하이브리드(벡터+전문검색) 융합 → (선택) 리랭커 재정렬. 벡터히트는 gap 판정용으로 함께 받는다.
    hits, vector_hits = await hybrid_search(
        question, embedder, k,
        shelf_patterns=shelf_patterns, reranker=reranker, facet_filters=facet_filters,
    )

    # gap 판정은 벡터 커버리지(코사인) 기준 — 정확어 히트가 순위를 바꿔도 커버리지는 의미유사도로.
    if log_gap and is_gap(vector_hits):
        try:
            await _record_gap(question, vector_hits)
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
