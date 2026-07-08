"""위키·RAG CLI — ADR-009.

사용:
    python -m apps.cli.wiki build [--limit N]     # 상품 도메인 이슈 → 위키 생성·임베딩
    python -m apps.cli.wiki ask "쿠팡 옵션 수정 안됨"   # RAG 유사 위키 검색·답변

전제: `docker compose up -d` → `python -m apps.cli.migrate`(009 포함).
"""

from __future__ import annotations

import asyncio
import sys

from apps.wiki_pipeline import ask, build_wikis
from infrastructure.postgres import connection as pg


async def _build(limit: int | None) -> None:
    result = await build_wikis(limit=limit)
    print(
        f"[build] llm={result.llm_mode} · 후보 {result.candidates}건 · "
        f"위키 생성 {result.wikis_built}건 · 실패 {result.failed}건"
    )


async def _ask(question: str) -> None:
    result = await ask(question)
    print(f"# 질문: {result.question}\n")
    print(f"## 답변\n{result.answer}\n")
    print(f"## 근거 위키 {len(result.hits)}건")
    for knowledge, score in result.hits:
        print(f"- [{score:.3f}] {knowledge.summary}  (출처: {', '.join(knowledge.sources)})")


async def _main(argv: list[str]) -> int:
    if not argv:
        print("사용법: wiki build [--limit N] | wiki ask \"질문\"", file=sys.stderr)
        return 2
    command = argv[0]
    try:
        if command == "build":
            limit = None
            if "--limit" in argv:
                limit = int(argv[argv.index("--limit") + 1])
            await _build(limit)
        elif command == "ask":
            if len(argv) < 2:
                print("질문을 입력하세요.", file=sys.stderr)
                return 2
            await _ask(argv[1])
        else:
            print(f"알 수 없는 명령: {command}", file=sys.stderr)
            return 2
    finally:
        await pg.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
