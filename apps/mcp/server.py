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

mcp = FastMCP("dip-knowledge-library")


@mcp.tool()
async def search_issues(query: str, limit: int = 8) -> str:
    """문의 내용/키워드로 유사 과거 이슈를 검색한다.

    Jira 이슈(제목·본문)에서 모든 키워드가 포함된 건을 찾아 상태·담당자·서가·요약을 반환한다.
    예: query="쿠팡 옵션 수정 안됨".
    """
    return await queries.search_issues(query, limit)


@mcp.tool()
async def get_expert_knowledge(query: str = "", limit: int = 5) -> str:
    """전문가가 작성한 검증된 지식(근본원인·플로우 분석)을 검색한다.

    예: query="요금 과충전" / "교환주문 플래그". query 비우면 전체 목록.
    """
    return await queries.expert_knowledge(query, limit)


@mcp.tool()
async def get_issue(jira_key: str) -> str:
    """이슈 키(예: PA20-19864)로 상세(본문 + 링크된 커밋)를 가져온다."""
    return await queries.issue_detail(jira_key)


@mcp.tool()
async def list_shelves(limit: int = 25) -> str:
    """도메인 서가(components) 목록과 각 이슈 수를 반환한다(둘러보기용)."""
    return await queries.list_shelves(limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
