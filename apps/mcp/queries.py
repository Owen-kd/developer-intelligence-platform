"""지식 도서관 조회 (MCP 서버용, 읽기 전용).

Postgres 에 쌓인 이슈/지식/커밋을 키워드로 검색해 Claude 가 읽기 좋은 텍스트로 반환한다.
LLM 을 쓰지 않는다 — 검색·조립만 한다(생성은 Claude 몫).
"""

from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import text

from infrastructure.embedding.reranker import Reranker
from infrastructure.postgres import connection as pg
from modules.knowledge.application.diversify import mmr_select
from modules.knowledge.application.fusion import hybrid_merge
from modules.knowledge.application.refinement import redact_pii
from modules.knowledge.application.wiki_service import WIKI_TYPE, wiki_embedding_text
from modules.knowledge.infrastructure.repository import PostgresKnowledgeRepository


def _patterns(query: str) -> list[str]:
    return [f"%{word}%" for word in query.split() if word.strip()]


def _shelf_cond(alias: str, shelf_patterns: tuple[str, ...]) -> str:
    """접근제어(ADR-010) 서가 필터 SQL 조각 — 이슈 components 가 패턴에 하나라도 매칭."""
    if not shelf_patterns:
        return ""
    return (
        f"AND EXISTS (SELECT 1 FROM jsonb_array_elements_text({alias}.components) s "
        "WHERE s ILIKE ANY(:shelfpats))"
    )


async def search_issues(
    query: str, limit: int = 8, shelf_patterns: tuple[str, ...] = ()
) -> str:
    """문의/키워드로 유사 이슈를 찾는다(모든 단어가 제목 또는 본문에 포함).

    `shelf_patterns`(접근제어) 가 주어지면 그 서가의 이슈만 반환한다.
    """
    patterns = _patterns(query)
    cond = (
        "(i.summary || ' ' || coalesce(i.description,'')) ILIKE ALL(:pats)" if patterns else "TRUE"
    )
    sql = text(
        f"""
        SELECT i.jira_key, i.status, i.priority, coalesce(i.assignee,'') AS assignee,
               i.components, i.summary, left(coalesce(i.description,''), 220) AS snippet,
               (SELECT count(*) FROM issue_commits ic WHERE ic.issue_id = i.id) AS commits
        FROM issues i WHERE {cond} {_shelf_cond("i", shelf_patterns)}
        ORDER BY i.updated_at DESC LIMIT :lim
        """
    )
    params: dict[str, object] = {"lim": limit}
    if patterns:
        params["pats"] = patterns
    if shelf_patterns:
        params["shelfpats"] = list(shelf_patterns)
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql, params)).all()

    if not rows:
        return f"'{query}' 관련 이슈를 찾지 못했습니다. (단어 수를 줄여보세요)"
    lines = [f"# '{query}' 유사 이슈 {len(rows)}건\n"]
    for r in rows:
        shelf = ", ".join(r.components) if r.components else "-"
        lines.append(
            f"## {r.jira_key} · {r.status}/{r.priority} · 담당 {r.assignee or '-'} · 서가 {shelf}\n"
            f"{redact_pii(r.summary)}\n"
            f"> {redact_pii(r.snippet.strip())}\n"
            f"(링크된 커밋 {r.commits}건)\n"
        )
    return "\n".join(lines)


async def expert_knowledge(query: str = "", limit: int = 5) -> str:
    """전문가가 작성한 검증(verified) 지식을 찾는다(근본원인·플로우 분석 등)."""
    patterns = _patterns(query)
    cond = "(summary || ' ' || (body->>'content')) ILIKE ALL(:pats)" if patterns else "TRUE"
    sql = text(
        f"""
        SELECT type, summary, body->>'content' AS content,
               body->>'code_refs' AS code_refs, sources
        FROM knowledge WHERE source = 'verified' AND {cond}
        ORDER BY created_at DESC LIMIT :lim
        """
    )
    params: dict[str, object] = {"lim": limit}
    if patterns:
        params["pats"] = patterns
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql, params)).all()

    if not rows:
        return f"'{query}' 관련 전문가 지식이 없습니다."
    lines = [f"# 전문가 검증 지식 {len(rows)}건 (신뢰등급: verified)\n"]
    for r in rows:
        src = ", ".join(r.sources) if r.sources else "-"
        lines.append(
            f"## [{r.type}] {r.summary}\n"
            f"코드참조: {r.code_refs or '-'}\n"
            f"출처: {src}\n\n{r.content}\n"
        )
    return "\n---\n".join(lines)


async def issue_detail(jira_key: str, shelf_patterns: tuple[str, ...] = ()) -> str:
    """이슈 키로 상세(본문 + 링크된 커밋)를 가져온다.

    `shelf_patterns`(접근제어) 가 주어지면 그 서가의 이슈가 아니면 미노출(존재도 숨김).
    """
    sql = text(
        f"""
        SELECT i.id, i.jira_key, i.type, i.status, i.priority,
               coalesce(i.assignee,'') AS assignee, coalesce(i.reporter,'') AS reporter,
               i.components, i.summary, coalesce(i.description,'') AS description
        FROM issues i WHERE i.jira_key = :k {_shelf_cond("i", shelf_patterns)}
        """
    )
    params: dict[str, object] = {"k": jira_key}
    if shelf_patterns:
        params["shelfpats"] = list(shelf_patterns)
    async with pg.get_engine().connect() as conn:
        issue = (await conn.execute(sql, params)).first()
        if issue is None:
            return f"{jira_key} 이슈를 찾지 못했습니다."
        commits = (
            await conn.execute(
                text(
                    "SELECT c.sha, c.author, c.message FROM issue_commits ic "
                    "JOIN commits c ON c.id = ic.commit_id WHERE ic.issue_id = :iid "
                    "ORDER BY c.committed_at"
                ),
                {"iid": issue.id},
            )
        ).all()

    shelf = ", ".join(issue.components) if issue.components else "-"
    out = [
        f"# {issue.jira_key} · {issue.type} · {issue.status}/{issue.priority}",
        f"담당 {issue.assignee or '-'} · 문의자 {issue.reporter or '-'} · 서가 {shelf}",
        f"\n**{redact_pii(issue.summary)}**\n",
        redact_pii(issue.description) if issue.description else "(본문 없음)",
        f"\n## 링크된 커밋 {len(commits)}건",
    ]
    for c in commits:
        first_line = (c.message.splitlines() or [""])[0]  # 빈 커밋 메시지 방어(IndexError)
        out.append(f"- `{c.sha[:10]}` {c.author}: {first_line[:70]}")
    return "\n".join(out)


async def search_wiki_hybrid(
    embedding: list[float],
    query_text: str,
    limit: int = 5,
    shelf_patterns: tuple[str, ...] = (),
    reranker: Reranker | None = None,
    rerank_pool: int = 20,
    diversify: bool = False,
    diversify_lambda: float = 0.7,
    facet_filters: Mapping[str, str] | None = None,
) -> str:
    """하이브리드 검색: 벡터(의미) + 전문검색(정확어)을 RRF 융합해 위키 top-k 반환.

    임베딩 생성은 호출자(서버)의 로컬 임베더 책임 — 이 함수는 검색·조립만 한다(생성/모델 없음).
    `reranker` 가 주어지면 융합 상위 `rerank_pool` 후보를 cross-encoder 로 재정렬한다.
    `diversify` 가 켜지면 같은 주제 중복을 MMR 로 억제해 top-k 를 다양화한다.
    `shelf_patterns`(접근제어, ADR-010) 가 주어지면 그 서가의 위키만 반환한다.
    `facet_filters`(ADR-015) 가 주어지면 그 축(도메인/채널/유형...)의 위키만 반환한다.
    """
    repo = PostgresKnowledgeRepository()
    vector_hits = await repo.search_semantic(
        embedding, limit=30, types=(WIKI_TYPE,),
        shelf_patterns=shelf_patterns, facet_filters=facet_filters,
    )
    keyword_hits = await repo.search_keyword(
        query_text, limit=30, types=(WIKI_TYPE,),
        shelf_patterns=shelf_patterns, facet_filters=facet_filters,
    )
    pool = rerank_pool if (reranker is not None or diversify) else limit
    hits = hybrid_merge(vector_hits, keyword_hits, pool)
    if reranker is not None and hits:
        docs = [wiki_embedding_text(k) for k, _ in hits]
        scores = await reranker.rerank(query_text, docs)
        ranked = sorted(zip(hits, scores, strict=True), key=lambda item: item[1], reverse=True)
        hits = [(k, float(score)) for (k, _cosine), score in ranked]
    if diversify and len(hits) > limit:
        embeddings = await repo.embeddings_for([k.id for k, _ in hits])
        hits = mmr_select(hits, embeddings, limit, diversify_lambda)
    hits = hits[:limit]
    if not hits:
        return (
            "관련 위키가 없습니다. (아직 위키 미생성일 수 있음 — "
            "`python -m apps.cli.wiki build` 로 생성)"
        )
    lines = [f"# 하이브리드 검색: 유사 위키 {len(hits)}건\n"]
    for knowledge, score in hits:
        body = knowledge.body if isinstance(knowledge.body, dict) else {}
        jira = next(
            (s.removeprefix("issue:") for s in knowledge.sources if s.startswith("issue:")),
            "-",
        )
        scope = str(body.get("scope", "")).strip()
        scope_target = str(body.get("scope_target", "")).strip()
        scope_suffix = f"·{scope_target}" if scope_target else ""
        scope_line = f"- 적용범위: {scope}{scope_suffix}\n" if scope else ""
        lines.append(
            f"## [{score:.2f}] {knowledge.summary} · {jira}\n"
            f"{scope_line}"
            f"- 증상: {str(body.get('symptom', ''))[:160]}\n"
            f"- 근본원인: {str(body.get('root_cause', ''))[:240]}\n"
            f"- 해결: {str(body.get('resolution', ''))[:160]}\n"
            f"- 코드참조: {body.get('code_refs') or '-'}\n"
        )
    return "\n".join(lines)


async def list_shelves(limit: int = 25, shelf_patterns: tuple[str, ...] = ()) -> str:
    """도메인 서가(components) 목록과 이슈 수.

    `shelf_patterns`(접근제어) 가 주어지면 허용된 서가만 노출한다.
    """
    where = "WHERE shelf ILIKE ANY(:shelfpats)" if shelf_patterns else ""
    sql = text(
        f"""
        SELECT shelf, count(*) AS n FROM (
            SELECT jsonb_array_elements_text(components) AS shelf FROM issues
        ) t {where}
        GROUP BY shelf ORDER BY n DESC LIMIT :lim
        """
    )
    params: dict[str, object] = {"lim": limit}
    if shelf_patterns:
        params["shelfpats"] = list(shelf_patterns)
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql, params)).all()
    lines = ["# 도메인 서가 (이슈 수)\n"]
    lines += [f"- {r.shelf}: {r.n}" for r in rows]
    return "\n".join(lines)
