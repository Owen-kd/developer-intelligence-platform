"""위키·RAG CLI — ADR-009.

사용:
    python -m apps.cli.wiki build [--limit N]     # 상품 도메인 이슈 → 위키 생성·임베딩
    python -m apps.cli.wiki backfill [--limit N]  # 아직 위키 없는 이슈만 배치 생성(backlog)
    python -m apps.cli.wiki ask "쿠팡 옵션 수정 안됨"   # RAG 유사 위키 검색·답변
    python -m apps.cli.wiki gaps                    # 되먹임: 답 못한 질문 + 위키화 후보

전제: `docker compose up -d` → `python -m apps.cli.migrate`(009 포함).
"""

from __future__ import annotations

import asyncio
import sys

from apps.wiki_pipeline import ask, build_wikis, gap_candidates, load_gap_records
from infrastructure.postgres import connection as pg
from modules.knowledge.application.gap_analysis import aggregate_gaps


async def _build(limit: int | None) -> None:
    result = await build_wikis(limit=limit)
    print(
        f"[build] llm={result.llm_mode} · 후보 {result.candidates} · "
        f"생성 {result.wikis_built} · 인덱스만 {result.index_only} · 실패 {result.failed}"
    )


async def _backfill(limit: int) -> None:
    result = await build_wikis(only_missing=True, limit=limit)
    print(
        f"[backfill] llm={result.llm_mode} · 대상 {result.candidates} · "
        f"생성 {result.wikis_built} · 인덱스만 {result.index_only} · 실패 {result.failed}"
    )


async def _ask(question: str) -> None:
    result = await ask(question)
    print(f"# 질문: {result.question}\n")
    print(f"## 답변\n{result.answer}\n")
    print(f"## 근거 위키 {len(result.hits)}건")
    for knowledge, score in result.hits:
        print(f"- [{score:.3f}] {knowledge.summary}  (출처: {', '.join(knowledge.sources)})")


async def _gaps() -> None:
    clusters = aggregate_gaps(await load_gap_records())
    if not clusters:
        print("아직 기록된 지식 구멍(gap)이 없습니다.")
        return
    print(f"# 지식 구멍 {len(clusters)}건 (자주 묻는데 커버리지 낮은 순)\n")
    for cluster in clusters:
        print(
            f"## {cluster.question}\n"
            f"- 물은 횟수 {cluster.occurrences} · 평균 최상위 유사도 {cluster.avg_top_score:.2f}"
        )
        candidates = await gap_candidates(cluster.question)
        if candidates:
            print("- 위키화 후보(아직 위키 없음):")
            for jira_key, summary in candidates:
                print(f"    · {jira_key} {summary[:50]}")
        print()


async def _main(argv: list[str]) -> int:
    if not argv:
        print(
            "사용법: wiki build|backfill [--limit N] | wiki ask \"질문\" | wiki gaps",
            file=sys.stderr,
        )
        return 2
    command = argv[0]
    try:
        if command == "build":
            limit = None
            if "--limit" in argv:
                limit = int(argv[argv.index("--limit") + 1])
            await _build(limit)
        elif command == "backfill":
            limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else 30
            await _backfill(limit)
        elif command == "ask":
            if len(argv) < 2:
                print("질문을 입력하세요.", file=sys.stderr)
                return 2
            await _ask(argv[1])
        elif command == "gaps":
            await _gaps()
        else:
            print(f"알 수 없는 명령: {command}", file=sys.stderr)
            return 2
    finally:
        await pg.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(sys.argv[1:])))
