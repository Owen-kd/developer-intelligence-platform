"""IssueRepository 구현 — 인메모리(테스트/데모) · Postgres(실적재).

두 어댑터 모두 같은 포트(`IssueRepository`)를 만족한다 → 서비스 코드 변경 없이 교체 가능.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime

from sqlalchemy import text

from infrastructure.postgres import connection as pg
from modules.jira.domain.entity import Comment, Issue
from modules.jira.domain.repository import IssueRepository


def _dt(value: str | None) -> datetime | None:
    """ISO-8601 문자열을 timestamptz 바인딩용 datetime 으로 변환한다."""
    return datetime.fromisoformat(value) if value else None


class InMemoryIssueRepository(IssueRepository):
    """프로세스 메모리 기반 저장소. 멱등 upsert 를 구현한다."""

    def __init__(self) -> None:
        self._by_key: dict[str, Issue] = {}

    async def upsert_issue(self, issue: Issue) -> str:
        existing = self._by_key.get(issue.jira_key)
        issue_id = existing.id if existing and existing.id else str(uuid.uuid4())
        # 기존 코멘트는 보존하고 이슈 필드만 갱신한다(append 지향).
        comments = existing.comments if existing else []
        self._by_key[issue.jira_key] = replace(issue, id=issue_id, comments=list(comments))
        return issue_id

    async def upsert_comment(self, issue_id: str, jira_key: str, comment: Comment) -> bool:
        issue = self._by_key.get(jira_key)
        if issue is None:
            return False
        if any(existing.external_id == comment.external_id for existing in issue.comments):
            return False
        issue.comments.append(comment)
        return True

    async def get_issue(self, jira_key: str) -> Issue | None:
        issue = self._by_key.get(jira_key)
        if issue is None:
            return None
        return replace(issue, comments=list(issue.comments))

    async def list_issues(self) -> list[Issue]:
        return [
            replace(issue, comments=list(issue.comments))
            for _, issue in sorted(self._by_key.items())
        ]


class PostgresIssueRepository(IssueRepository):
    """Postgres 저장소. `issues`/`comments` 테이블에 멱등 upsert."""

    async def upsert_issue(self, issue: Issue) -> str:
        query = text(
            """
            INSERT INTO issues
                (jira_key, type, status, priority, summary, assignee, created_at, updated_at)
            VALUES (:jira_key, :type, :status, :priority, :summary, :assignee,
                    CAST(:created_at AS timestamptz), CAST(:updated_at AS timestamptz))
            ON CONFLICT (jira_key) DO UPDATE SET
                type = EXCLUDED.type,
                status = EXCLUDED.status,
                priority = EXCLUDED.priority,
                summary = EXCLUDED.summary,
                assignee = EXCLUDED.assignee,
                updated_at = EXCLUDED.updated_at,
                synced_at = now()
            RETURNING id
            """
        )
        async with pg.get_engine().begin() as conn:
            result = await conn.execute(
                query,
                {
                    "jira_key": issue.jira_key,
                    "type": issue.type,
                    "status": issue.status,
                    "priority": issue.priority,
                    "summary": issue.summary,
                    "assignee": issue.assignee,
                    "created_at": _dt(issue.created_at),
                    "updated_at": _dt(issue.updated_at),
                },
            )
            issue_id = result.scalar_one()
        return str(issue_id)

    async def upsert_comment(self, issue_id: str, jira_key: str, comment: Comment) -> bool:
        query = text(
            """
            INSERT INTO comments (issue_id, external_id, author, body, created_at)
            VALUES (:issue_id, :external_id, :author, :body, CAST(:created_at AS timestamptz))
            ON CONFLICT (issue_id, external_id) DO NOTHING
            RETURNING id
            """
        )
        async with pg.get_engine().begin() as conn:
            result = await conn.execute(
                query,
                {
                    "issue_id": issue_id,
                    "external_id": comment.external_id,
                    "author": comment.author,
                    "body": comment.body,
                    "created_at": _dt(comment.created_at),
                },
            )
            return result.first() is not None

    async def get_issue(self, jira_key: str) -> Issue | None:
        async with pg.get_engine().connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT id, jira_key, type, status, priority, summary, "
                        "created_at, updated_at FROM issues WHERE jira_key = :k"
                    ),
                    {"k": jira_key},
                )
            ).first()
            if row is None:
                return None
            comment_rows = (
                await conn.execute(
                    text(
                        "SELECT external_id, author, body, created_at "
                        "FROM comments WHERE issue_id = :iid ORDER BY created_at"
                    ),
                    {"iid": row.id},
                )
            ).all()
        return Issue(
            id=str(row.id),
            jira_key=row.jira_key,
            type=row.type,
            status=row.status,
            priority=row.priority,
            summary=row.summary,
            created_at=str(row.created_at),
            updated_at=str(row.updated_at),
            comments=[
                Comment(
                    external_id=c.external_id,
                    author=c.author,
                    body=c.body,
                    created_at=str(c.created_at),
                )
                for c in comment_rows
            ],
        )

    async def list_issues(self) -> list[Issue]:
        async with pg.get_engine().connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT id, jira_key, type, status, priority, summary, "
                        "created_at, updated_at FROM issues ORDER BY jira_key"
                    )
                )
            ).all()
        return [
            Issue(
                id=str(row.id),
                jira_key=row.jira_key,
                type=row.type,
                status=row.status,
                priority=row.priority,
                summary=row.summary,
                created_at=str(row.created_at),
                updated_at=str(row.updated_at),
            )
            for row in rows
        ]
