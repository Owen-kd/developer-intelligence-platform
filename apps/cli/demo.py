"""End-to-end 데모 — 전체 파이프라인을 1회 실행하고 요약을 출력한다.

수집 → 그래프 → Knowledge 승격 → Triage/Impact Agent → Incident Library.
외부 시스템 없이(인메모리) 전 과정을 보여준다.

사용:
    python -m apps.cli.demo
"""

from __future__ import annotations

import asyncio

from apps.composition import build_and_run
from shared.logger import get_logger

_logger = get_logger("cli.demo")


async def _main() -> None:
    app = await build_and_run()

    issues = await app.issue_repo.list_issues()
    incidents = await app.incident_repo.list_all()

    _logger.info(
        "demo.summary",
        issues=len(issues),
        events=len(app.store.events),
        incidents=len(incidents),
        audit_entries=len(app.audit.entries),
    )
    for issue in issues:
        assert issue.id is not None
        knowledge = await app.knowledge_repo.list_by_issue(issue.id)
        types = sorted({item.type for item in knowledge})
        _logger.info("demo.issue", jira_key=issue.jira_key, knowledge_types=types)


if __name__ == "__main__":
    asyncio.run(_main())
