"""Obsidian export CLI.

사용:
    python -m apps.cli.obsidian export [--out vault]   # 위키 → Obsidian 마크다운 볼트

볼트를 Obsidian 으로 열면 관련 이슈가 [[위키링크]]·그래프 뷰로 이어진다.
전제: `docker compose up -d` + 위키 생성됨(`python -m apps.cli.wiki build`).
"""

from __future__ import annotations

import asyncio
import sys

from apps.obsidian_export import export_vault
from infrastructure.postgres import connection as pg

_DEFAULT_OUT = "vault"


async def _export(out: str) -> None:
    result = await export_vault(out)
    print(
        f"[obsidian] 볼트 '{result.out_dir}' 에 위키 {result.written}건 내보냄 "
        f"(건너뜀 {result.skipped}) · index.md 포함. Obsidian 으로 이 폴더를 여세요."
    )


async def _main(argv: list[str]) -> int:
    if not argv or argv[0] != "export":
        print("사용법: obsidian export [--out vault]", file=sys.stderr)
        return 2
    out = argv[argv.index("--out") + 1] if "--out" in argv else _DEFAULT_OUT
    try:
        await _export(out)
    finally:
        await pg.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
