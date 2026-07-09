"""RAG 질의 라우터 (루프3-Pull) — 자연어 질문 → 유사 위키 검색 → LLM 답변 + 출처.

근거를 못 찾거나 약하면 질문이 query_gaps 에 남는다(되먹임). 지식 구멍 조회도 제공한다.
임베더는 프로세스당 1회 로딩(lru_cache)한다.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from apps.api.dependencies.auth import require_principal
from apps.wiki_pipeline import ask as run_ask
from apps.wiki_pipeline import load_gap_records
from infrastructure.embedding.client import Embedder, FastEmbedEmbedder
from modules.knowledge.application.gap_analysis import aggregate_gaps
from shared.config.settings import get_settings

router = APIRouter(
    prefix="/ask",
    tags=["ask"],
    dependencies=[Depends(require_principal)],
)


@lru_cache
def _embedder() -> Embedder:
    settings = get_settings()
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim)


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)


class WikiHit(BaseModel):
    jira_key: str
    summary: str
    score: float
    sources: list[str]


class AskResponse(BaseModel):
    question: str
    answer: str
    hits: list[WikiHit]


class GapView(BaseModel):
    question: str
    occurrences: int
    avg_top_score: float
    variants: int


@router.post("", response_model=AskResponse)
async def ask_question(req: AskRequest) -> AskResponse:
    result = await run_ask(req.question, k=req.k, embedder=_embedder())
    return AskResponse(
        question=result.question,
        answer=result.answer,
        hits=[
            WikiHit(
                jira_key=_jira_of(knowledge.sources, knowledge.issue_id),
                summary=knowledge.summary,
                score=round(score, 4),
                sources=list(knowledge.sources),
            )
            for knowledge, score in result.hits
        ],
    )


@router.get("/gaps", response_model=list[GapView])
async def list_gaps(limit: int = 20) -> list[GapView]:
    """지식 구멍(되먹임) — 유사질문을 묶어 '자주 묻는데 커버리지 낮은 순'으로."""
    clusters = aggregate_gaps(await load_gap_records(), limit=limit)
    return [
        GapView(
            question=cluster.question,
            occurrences=cluster.occurrences,
            avg_top_score=round(cluster.avg_top_score, 4),
            variants=cluster.variants,
        )
        for cluster in clusters
    ]


def _jira_of(sources: tuple[str, ...], fallback: str) -> str:
    for source in sources:
        if source.startswith("issue:"):
            return source.removeprefix("issue:")
    return fallback or "-"
