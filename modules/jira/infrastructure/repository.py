"""IssueRepository 구현 — 인메모리(테스트/데모) · Postgres(실적재).

두 어댑터 모두 같은 포트(`IssueRepository`)를 만족한다 → 서비스 코드 변경 없이 교체 가능.
"""

from __future__ import annotations

import json
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
                (jira_key, type, status, priority, summary, assignee, reporter,
                 description, labels, components, created_at, updated_at)
            VALUES (:jira_key, :type, :status, :priority, :summary, :assignee, :reporter,
                    :description, CAST(:labels AS jsonb), CAST(:components AS jsonb),
                    CAST(:created_at AS timestamptz), CAST(:updated_at AS timestamptz))
            ON CONFLICT (jira_key) DO UPDATE SET
                type = EXCLUDED.type,
                status = EXCLUDED.status,
                priority = EXCLUDED.priority,
                summary = EXCLUDED.summary,
                assignee = EXCLUDED.assignee,
                reporter = EXCLUDED.reporter,
                description = EXCLUDED.description,
                labels = EXCLUDED.labels,
                components = EXCLUDED.components,
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
                    "reporter": issue.reporter,
                    "description": issue.description,
                    "labels": json.dumps(issue.labels),
                    "components": json.dumps(issue.components),
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

    async def iter_for_classification(
        self,
    ) -> list[tuple[str, str, str, list[str], list[str]]]:
        """분류 입력(id, jira_key, summary, components, labels)을 전량 조회한다 — Facet 부트스트랩.

        knowledge 의 순수 분류기가 소비할 원시 필드만 돌려준다(모듈 간 타입 결합 회피).
        """
        async with pg.get_engine().connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT id, jira_key, COALESCE(summary,'') AS summary, "
                        "components, labels FROM issues"
                    )
                )
            ).all()
        return [
            (
                str(row.id),
                row.jira_key,
                row.summary,
                list(row.components or []),
                list(row.labels or []),
            )
            for row in rows
        ]

    async def facets_exist(self, issue_id: str) -> bool:
        """이슈에 이미 facet 분류가 있는지(멱등·비파괴 자동분류용)."""
        query = text("SELECT 1 FROM issue_facets WHERE issue_id = :iid LIMIT 1")
        async with pg.get_engine().connect() as conn:
            return (await conn.execute(query, {"iid": issue_id})).first() is not None

    async def save_facets(
        self, issue_id: str, facets: dict[str, str], method: str = "rule"
    ) -> None:
        """이슈 분류(6축)를 upsert 한다 — 원본 불변, 재분류는 덮어쓰기(ADR-015)."""
        query = text(
            """
            INSERT INTO issue_facets
                (issue_id, domain, feature_area, action, channel,
                 issue_type, team, area, method, classified_at)
            VALUES
                (:iid, :domain, :feature_area, :action, :channel,
                 :issue_type, :team, :area, :method, now())
            ON CONFLICT (issue_id) DO UPDATE SET
                domain = EXCLUDED.domain, feature_area = EXCLUDED.feature_area,
                action = EXCLUDED.action, channel = EXCLUDED.channel,
                issue_type = EXCLUDED.issue_type, team = EXCLUDED.team,
                area = EXCLUDED.area, method = EXCLUDED.method,
                classified_at = EXCLUDED.classified_at
            """
        )
        async with pg.get_engine().begin() as conn:
            await conn.execute(query, {"iid": issue_id, "method": method, **facets})
