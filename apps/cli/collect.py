"""수집 전용 CLI — 실 Jira 대량 수집 + 저비용 정제(LLM 0).

LLM 판단(triage/impact)과 분리된 "수집·정제·축적" 단계다.
수집량은 `JIRA_MAX_ISSUES`(예: 1000)로 조절한다. 재실행 시 신규/변경만 반영(멱등).

사용:
    docker compose up -d && python -m apps.cli.migrate
    JIRA_MAX_ISSUES=1000 python -m apps.cli.collect
"""

from __future__ import annotations

import asyncio

from apps.composition_pg import collect_and_refine
from infrastructure.postgres import connection as pg
from shared.logger import get_logger

_logger = get_logger("cli.collect")


async def _main() -> None:
    try:
        result = await collect_and_refine()
        _logger.info(
            "collect.done",
            jira_mode=result.jira_mode,
            git_mode=result.git_mode,
            issues_synced=result.issues_synced,
            issues_created=result.issues_created,
            commits_synced=result.commits_synced,
            links_created=result.links_created,
            refined=result.refined,
            total_in_db=result.total_in_db,
        )
    finally:
        await pg.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
