"""End-to-end 데모 (Postgres) — 전체 파이프라인을 1회 실행하고 요약을 출력한다.

인메모리 데모([demo.py](demo.py))의 Postgres 판. 데이터가 DB 에 영속되므로,
재실행/재시작해도 조회가 유지되는지 확인할 수 있다.

사용:
    docker compose up -d
    python -m apps.cli.migrate        # 스키마 적용(001~003)
    python -m apps.cli.demo_pg        # 파이프라인 실행 + 요약
    # (라이브 LLM은 .env ANTHROPIC_API_KEY 가 있을 때 자동 사용 — 과금/외부 전송 주의)
"""

from __future__ import annotations

import asyncio

from apps.composition_pg import build_and_run_pg
from infrastructure.postgres import connection as pg
from shared.logger import get_logger

_logger = get_logger("cli.demo_pg")


async def _main() -> None:
    try:
        app = await build_and_run_pg()

        issues = await app.issue_repo.list_issues()
        incidents = await app.incident_repo.list_all()

        _logger.info(
            "demo_pg.summary",
            jira_mode=app.jira_mode,
            llm_mode=app.llm_mode,
            issues=len(issues),
            incidents=len(incidents),
            audit_entries=len(app.audit.entries),
        )
        for issue in issues:
            if issue.id is None:
                continue
            knowledge = await app.knowledge_repo.list_by_issue(issue.id)
            types = sorted({item.type for item in knowledge})
            _logger.info("demo_pg.issue", jira_key=issue.jira_key, knowledge_types=types)
    finally:
        await pg.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
