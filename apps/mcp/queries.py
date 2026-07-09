"""지식 도서관 조회 (MCP 서버용, 읽기 전용).

Postgres 에 쌓인 이슈/지식/커밋을 키워드로 검색해 Claude 가 읽기 좋은 텍스트로 반환한다.
LLM 을 쓰지 않는다 — 검색·조립만 한다(생성은 Claude 몫).
"""

from __future__ import annotations

from sqlalchemy import text

from infrastructure.postgres import connection as pg
from modules.knowledge.application.wiki_service import WIKI_TYPE
from modules.knowledge.infrastructure.repository import PostgresKnowledgeRepository


def _patterns(query: str) -> list[str]:
    return [f"%{word}%" for word in query.split() if word.strip()]


async def search_issues(query: str, limit: int = 8) -> str:
    """문의/키워드로 유사 이슈를 찾는다(모든 단어가 제목 또는 본문에 포함)."""
    patterns = _patterns(query)
    cond = (
        "(i.summary || ' ' || coalesce(i.description,'')) ILIKE ALL(:pats)" if patterns else "TRUE"
    )
    sql = text(
        f"""
        SELECT i.jira_key, i.status, i.priority, coalesce(i.assignee,'') AS assignee,
               i.components, i.summary, left(coalesce(i.description,''), 220) AS snippet,
               (SELECT count(*) FROM issue_commits ic WHERE ic.issue_id = i.id) AS commits
        FROM issues i WHERE {cond}
        ORDER BY i.updated_at DESC LIMIT :lim
        """
    )
    params: dict[str, object] = {"lim": limit}
    if patterns:
        params["pats"] = patterns
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql, params)).all()

    if not rows:
        return f"'{query}' 관련 이슈를 찾지 못했습니다. (단어 수를 줄여보세요)"
    lines = [f"# '{query}' 유사 이슈 {len(rows)}건\n"]
    for r in rows:
        shelf = ", ".join(r.components) if r.components else "-"
        lines.append(
            f"## {r.jira_key} · {r.status}/{r.priority} · 담당 {r.assignee or '-'} · 서가 {shelf}\n"
            f"{r.summary}\n"
            f"> {r.snippet.strip()}\n"
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


async def issue_detail(jira_key: str) -> str:
    """이슈 키로 상세(본문 + 링크된 커밋)를 가져온다."""
    sql = text(
        """
        SELECT id, jira_key, type, status, priority, coalesce(assignee,'') AS assignee,
               coalesce(reporter,'') AS reporter, components, summary,
               coalesce(description,'') AS description
        FROM issues WHERE jira_key = :k
        """
    )
    async with pg.get_engine().connect() as conn:
        issue = (await conn.execute(sql, {"k": jira_key})).first()
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
        f"\n**{issue.summary}**\n",
        issue.description or "(본문 없음)",
        f"\n## 링크된 커밋 {len(commits)}건",
    ]
    for c in commits:
        out.append(f"- `{c.sha[:10]}` {c.author}: {c.message.splitlines()[0][:70]}")
    return "\n".join(out)


async def search_wiki_by_vector(embedding: list[float], limit: int = 5) -> str:
    """질의 임베딩과 의미가 유사한 위키를 top-k 로 반환한다(벡터 RAG, 키워드 아님).

    임베딩 생성은 호출자(서버)의 로컬 임베더 책임 — 이 함수는 검색·조립만 한다(생성/모델 없음).
    """
    repo = PostgresKnowledgeRepository()
    hits = await repo.search_semantic(embedding, limit=limit, types=(WIKI_TYPE,))
    if not hits:
        return (
            "관련 위키가 없습니다. (아직 위키 미생성일 수 있음 — "
            "`python -m apps.cli.wiki build` 로 생성)"
        )
    lines = [f"# 의미검색: 유사 위키 {len(hits)}건\n"]
    for knowledge, score in hits:
        body = knowledge.body if isinstance(knowledge.body, dict) else {}
        jira = next(
            (s.removeprefix("issue:") for s in knowledge.sources if s.startswith("issue:")),
            "-",
        )
        lines.append(
            f"## [{score:.2f}] {knowledge.summary} · {jira}\n"
            f"- 증상: {str(body.get('symptom', ''))[:160]}\n"
            f"- 근본원인: {str(body.get('root_cause', ''))[:240]}\n"
            f"- 해결: {str(body.get('resolution', ''))[:160]}\n"
            f"- 코드참조: {body.get('code_refs') or '-'}\n"
        )
    return "\n".join(lines)


async def list_shelves(limit: int = 25) -> str:
    """도메인 서가(components) 목록과 이슈 수."""
    sql = text(
        """
        SELECT jsonb_array_elements_text(components) AS shelf, count(*) AS n
        FROM issues GROUP BY 1 ORDER BY 2 DESC LIMIT :lim
        """
    )
    async with pg.get_engine().connect() as conn:
        rows = (await conn.execute(sql, {"lim": limit})).all()
    lines = ["# 도메인 서가 (이슈 수)\n"]
    lines += [f"- {r.shelf}: {r.n}" for r in rows]
    return "\n".join(lines)
