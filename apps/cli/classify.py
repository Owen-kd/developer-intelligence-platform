"""Facet 분류 CLI — ADR-015.

사용:
    python -m apps.cli.classify bootstrap    # 전 이슈 규칙 분류 → issue_facets 적재(LLM 0)

전제: `docker compose up -d` + `python -m apps.cli.migrate`(013 포함).
"""

from __future__ import annotations

import asyncio
import sys

from apps.classify_bootstrap import classify_all
from infrastructure.postgres import connection as pg


async def _bootstrap() -> None:
    result = await classify_all()
    print(f"[classify] {result.classified}/{result.total}건 분류 적재(규칙). 축별 채움:")
    for field, count in result.filled.items():
        pct = count / result.total * 100 if result.total else 0.0
        print(f"  {field:12}: {pct:5.1f}%  ({count})")


async def _main(argv: list[str]) -> int:
    if not argv or argv[0] != "bootstrap":
        print("사용법: classify bootstrap", file=sys.stderr)
        return 2
    try:
        await _bootstrap()
    finally:
        await pg.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
