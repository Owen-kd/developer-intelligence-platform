"""Facet 분류 CLI — ADR-015.

사용:
    python -m apps.cli.classify bootstrap        # 전 이슈 규칙 분류 → issue_facets 적재(LLM 0)
    python -m apps.cli.classify enrich [--limit N]  # 규칙이 미상인 축을 LLM 으로 보강(비용 발생)

전제: `docker compose up -d` + `python -m apps.cli.migrate`(013 포함).
"""

from __future__ import annotations

import asyncio
import sys

from apps.classify_bootstrap import classify_all
from apps.classify_enrich import enrich_missing
from infrastructure.postgres import connection as pg


async def _bootstrap() -> None:
    result = await classify_all()
    print(f"[classify] {result.classified}/{result.total}건 분류 적재(규칙). 축별 채움:")
    for field, count in result.filled.items():
        pct = count / result.total * 100 if result.total else 0.0
        print(f"  {field:12}: {pct:5.1f}%  ({count})")


async def _enrich(limit: int | None) -> None:
    result = await enrich_missing(limit=limit)
    print(
        f"[enrich] 대상 {result.targets}건 · 보강됨 {result.enriched} · 실패 {result.failed} (LLM)"
    )


async def _main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("bootstrap", "enrich"):
        print("사용법: classify bootstrap | classify enrich [--limit N]", file=sys.stderr)
        return 2
    try:
        if argv[0] == "bootstrap":
            await _bootstrap()
        else:
            limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
            await _enrich(limit)
    finally:
        await pg.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
