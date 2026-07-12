"""DIP 지식 도서관 — MCP 서버.

Claude Desktop / Claude Code / Kiro 등이 이 서버를 붙여 도서관을 검색한다.
**별도 LLM 불필요** — 생성은 Claude 가, 이 서버는 데이터(검색 결과)만 제공한다.

실행:
    docker compose up -d
    python -m apps.mcp.server        # stdio MCP 서버

Claude Desktop 연결: README/응답의 설정 JSON 참고.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from apps.mcp import queries
from dip_platform.access import allowed_patterns, load_policies
from infrastructure.embedding.client import get_embedder  # 프로세스 단일 캐시 임베더
from infrastructure.embedding.reranker import Reranker, get_reranker
from shared.config.settings import get_settings

mcp = FastMCP("dip-knowledge-library")


def _access_shelf_patterns() -> tuple[str, ...] | None:
    """접근제어(ADR-010)가 켜져 있으면 이 프로세스 팀(DIP_TEAM)의 허용 서가를 반환.

    None = 접근제어 OFF(제한 없음). 빈 튜플 = 팀 미허가(deny).
    """
    settings = get_settings()
    if not settings.access_control_enabled:
        return None
    return allowed_patterns(load_policies(settings.access_policy_file), settings.dip_team)


def _reranker() -> Reranker | None:
    """리랭커가 켜져 있으면(rerank_enabled) 프로세스 단일 인스턴스, 꺼져 있으면 None."""
    if not get_settings().rerank_enabled:
        return None
    return get_reranker()


@mcp.tool()
async def search_issues(query: str, limit: int = 8) -> str:
    """문의 내용/키워드로 유사 과거 이슈를 검색한다.

    Jira 이슈(제목·본문)에서 모든 키워드가 포함된 건을 찾아 상태·담당자·서가·요약을 반환한다.
    예: query="쿠팡 옵션 수정 안됨".
    """
    patterns = _access_shelf_patterns()
    if patterns is not None and not patterns:
        return "열람 권한이 없습니다(DIP_TEAM 미지정/미허가)."
    return await queries.search_issues(query, limit, patterns or ())


@mcp.tool()
async def get_expert_knowledge(query: str = "", limit: int = 5) -> str:
    """전문가가 작성한 검증된 지식(근본원인·플로우 분석)을 검색한다.

    예: query="요금 과충전" / "교환주문 플래그". query 비우면 전체 목록.
    """
    # 검증 지식은 이슈에 매이지 않아 서가 필터가 불가 → 접근제어 ON 시 미허가 팀은 차단(deny).
    # 허가된 팀에는 전사 공유 지식으로 노출한다(후속: 전문가 문서에 서가 태깅).
    patterns = _access_shelf_patterns()
    if patterns is not None and not patterns:
        return "열람 권한이 없습니다(DIP_TEAM 미지정/미허가)."
    return await queries.expert_knowledge(query, limit)


@mcp.tool()
async def search_wiki(
    query: str,
    limit: int = 5,
    domain: str = "",
    channel: str = "",
    issue_type: str = "",
) -> str:
    """자연어 질문으로 유사 위키를 검색한다 — 하이브리드(의미 + 정확어) RAG + 리랭커.

    의미 유사도(벡터)와 정확 식별자(전문검색: option_code/GTIN/쿠팡 등)를 RRF 로 융합하고,
    로컬 cross-encoder 리랭커(ADR-013)로 상위 후보를 재정렬해 정밀도를 높인다.
    예: query="쿠팡에서 옵션이 수정이 안돼요" → 관련 위키를 증상·근본원인·해결과 함께 반환.
    facet 필터(ADR-015)로 좁힐 수 있다: domain(product/order/stock/pay/...),
    channel(쿠팡/ESM/스마트스토어/...), issue_type(오류/기능개선/문의/정책). 비우면 전체.
    """
    patterns = _access_shelf_patterns()
    if patterns is not None and not patterns:
        return "열람 권한이 없습니다(DIP_TEAM 미지정/미허가). 관리자에게 서가 권한을 요청하세요."
    settings = get_settings()
    facet_filters = {
        axis: val
        for axis, val in (("domain", domain), ("channel", channel), ("issue_type", issue_type))
        if val
    }
    embedding = await get_embedder().embed_query(query)
    return await queries.search_wiki_hybrid(
        embedding,
        query,
        limit,
        patterns or (),
        reranker=_reranker(),
        rerank_pool=settings.rerank_pool,
        diversify=settings.diversify_enabled,
        diversify_lambda=settings.diversify_lambda,
        facet_filters=facet_filters or None,
    )


@mcp.tool()
async def get_issue(jira_key: str) -> str:
    """이슈 키(예: PA20-19864)로 상세(본문 + 링크된 커밋)를 가져온다."""
    patterns = _access_shelf_patterns()
    if patterns is not None and not patterns:
        return "열람 권한이 없습니다(DIP_TEAM 미지정/미허가)."
    return await queries.issue_detail(jira_key, patterns or ())


@mcp.tool()
async def list_shelves(limit: int = 25) -> str:
    """도메인 서가(components) 목록과 각 이슈 수를 반환한다(둘러보기용)."""
    patterns = _access_shelf_patterns()
    if patterns is not None and not patterns:
        return "열람 권한이 없습니다(DIP_TEAM 미지정/미허가)."
    return await queries.list_shelves(limit, patterns or ())


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
