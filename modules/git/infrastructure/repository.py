"""CommitRepository 구현 — 인메모리(테스트/데모) · Postgres(실적재)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime

from sqlalchemy import text

from infrastructure.postgres import connection as pg
from modules.git.domain.entity import Commit
from modules.git.domain.repository import CommitRepository


def _dt(value: str | None) -> datetime | None:
    """ISO-8601 문자열을 timestamptz 바인딩용 datetime 으로 변환한다."""
    return datetime.fromisoformat(value) if value else None


class InMemoryCommitRepository(CommitRepository):
    """프로세스 메모리 기반 커밋 저장소."""

    def __init__(self) -> None:
        self._by_sha: dict[str, Commit] = {}
        self._links: set[tuple[str, str]] = set()
        self._issue_ids: dict[str, str] = {}

    async def upsert_commit(self, commit: Commit) -> str:
        existing = self._by_sha.get(commit.sha)
        commit_id = existing.id if existing and existing.id else str(uuid.uuid4())
        self._by_sha[commit.sha] = replace(commit, id=commit_id)
        return commit_id

    async def link(self, issue_id: str, commit_id: str) -> bool:
        key = (issue_id, commit_id)
        if key in self._links:
            return False
        self._links.add(key)
        return True

    async def remember_issue(self, jira_key: str, issue_id: str) -> None:
        self._issue_ids[jira_key] = issue_id

    async def resolve_issue(self, jira_key: str) -> str | None:
        return self._issue_ids.get(jira_key)


class PostgresCommitRepository(CommitRepository):
    """Postgres 커밋 저장소. jira_key 해석은 `issues` 테이블을 읽어 수행한다."""

    async def upsert_commit(self, commit: Commit) -> str:
        query = text(
            """
            INSERT INTO commits (sha, author, message, committed_at)
            VALUES (:sha, :author, :message, CAST(:committed_at AS timestamptz))
            ON CONFLICT (sha) DO UPDATE SET
                author = EXCLUDED.author,
                message = EXCLUDED.message,
                committed_at = EXCLUDED.committed_at,
                synced_at = now()
            RETURNING id
            """
        )
        async with pg.get_engine().begin() as conn:
            result = await conn.execute(
                query,
                {
                    "sha": commit.sha,
                    "author": commit.author,
                    "message": commit.message,
                    "committed_at": _dt(commit.committed_at),
                },
            )
            return str(result.scalar_one())

    async def link(self, issue_id: str, commit_id: str) -> bool:
        query = text(
            """
            INSERT INTO issue_commits (issue_id, commit_id)
            VALUES (:issue_id, :commit_id)
            ON CONFLICT (issue_id, commit_id) DO NOTHING
            RETURNING commit_id
            """
        )
        async with pg.get_engine().begin() as conn:
            result = await conn.execute(
                query, {"issue_id": issue_id, "commit_id": commit_id}
            )
            return result.first() is not None

    async def remember_issue(self, jira_key: str, issue_id: str) -> None:
        # Postgres 에서는 issues 테이블이 이미 매핑을 가지므로 별도 보관이 불필요하다.
        return None

    async def resolve_issue(self, jira_key: str) -> str | None:
        async with pg.get_engine().connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT id FROM issues WHERE jira_key = :k"), {"k": jira_key}
                )
            ).first()
        return str(row.id) if row is not None else None
