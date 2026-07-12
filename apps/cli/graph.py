"""지식 그래프 CLI — ADR-016.

사용:
    python -m apps.cli.graph backfill    # Postgres → Neo4j 그래프 적재(멱등)

전제: `docker compose up -d neo4j` + Postgres 데이터(이슈/위키/facet).
"""

from __future__ import annotations

import asyncio
import sys

from apps.graph_backfill import backfill_graph
from infrastructure.postgres import connection as pg


async def _backfill() -> None:
    result = await backfill_graph()
    print(f"[graph] Neo4j 적재 완료 — 노드 {result.nodes} · 엣지 {result.edges}")


async def _main(argv: list[str]) -> int:
    if not argv or argv[0] != "backfill":
        print("사용법: graph backfill", file=sys.stderr)
        return 2
    try:
        await _backfill()
    finally:
        await pg.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
