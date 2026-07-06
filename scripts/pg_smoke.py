"""임시 Postgres 대상 어댑터 스모크(수동 실행용, 테스트 수집 대상 아님).

migrations 적용 후 PostgresIssueRepository / PostgresEventStore 가
실제 DB 에서 동작하는지 확인한다.
"""

from __future__ import annotations

import asyncio

from apps.cli.migrate import apply_migrations
from dip_platform.event import Event
from infrastructure.postgres import connection as pg
from infrastructure.postgres.event_store import PostgresEventStore
from modules.jira.domain.entity import Comment, Issue
from modules.jira.domain.events import IssueCreatedPayload
from modules.jira.infrastructure.repository import PostgresIssueRepository


async def main() -> None:
    applied = await apply_migrations()
    print("migrations:", applied)

    repo = PostgresIssueRepository()
    issue = Issue(
        jira_key="DIP-1",
        type="Bug",
        status="In Progress",
        priority="High",
        summary="결제 API 타임아웃",
        created_at="2026-07-01T09:00:00+00:00",
        updated_at="2026-07-02T10:30:00+00:00",
    )
    issue_id = await repo.upsert_issue(issue)
    # 멱등 확인: 같은 키 재-upsert 는 같은 id.
    assert issue_id == await repo.upsert_issue(issue)

    added = await repo.upsert_comment(
        issue_id, "DIP-1", Comment("c-1", "jieun", "커넥션 풀 고갈", "2026-07-01T11:00:00+00:00")
    )
    assert added is True
    assert await repo.upsert_comment(
        issue_id, "DIP-1", Comment("c-1", "jieun", "커넥션 풀 고갈", "2026-07-01T11:00:00+00:00")
    ) is False  # 멱등

    store = PostgresEventStore()
    await store.append(Event("IssueCreated", IssueCreatedPayload(issue_id, "DIP-1")))
    events = await store.list_by_name("IssueCreated")

    fetched = await repo.get_issue("DIP-1")
    assert fetched is not None
    print("issue:", fetched.jira_key, "comments:", len(fetched.comments), "events:", len(events))
    print("PG SMOKE OK")
    await pg.dispose()


if __name__ == "__main__":
    asyncio.run(main())
