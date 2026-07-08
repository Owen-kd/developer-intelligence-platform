"""Knowledge 저장소 + 원천 리더 구현 — 인메모리 · Postgres."""

from __future__ import annotations

import json

from sqlalchemy import text

from infrastructure.postgres import connection as pg
from modules.knowledge.domain.entity import IssueSnapshot, Knowledge
from modules.knowledge.domain.repository import IssueSourceReader, KnowledgeRepository


class InMemoryKnowledgeRepository(KnowledgeRepository):
    """프로세스 메모리 기반 Knowledge Library(append 지향)."""

    def __init__(self) -> None:
        self._items: list[Knowledge] = []

    async def save(self, knowledge: Knowledge) -> None:
        self._items.append(knowledge)

    async def list_by_issue(self, issue_id: str) -> list[Knowledge]:
        return [item for item in self._items if item.issue_id == issue_id]

    async def get(self, knowledge_id: str) -> Knowledge | None:
        return next((item for item in self._items if item.id == knowledge_id), None)

    async def list_by_type(self, knowledge_type: str) -> list[Knowledge]:
        return [item for item in self._items if item.type == knowledge_type]


class InMemoryIssueSourceReader(IssueSourceReader):
    """주입된 스냅샷을 반환하는 읽기 포트(데모/테스트).

    apps 조립 계층이 수집 결과로부터 스냅샷을 만들어 등록한다(apps→modules 허용).
    """

    def __init__(self) -> None:
        self._snapshots: dict[str, IssueSnapshot] = {}

    def add(self, snapshot: IssueSnapshot) -> None:
        self._snapshots[snapshot.issue_id] = snapshot

    async def get_snapshot(self, issue_id: str) -> IssueSnapshot | None:
        return self._snapshots.get(issue_id)


class PostgresKnowledgeRepository(KnowledgeRepository):
    """`knowledge` 테이블 기반 Library."""

    async def save(self, knowledge: Knowledge) -> None:
        query = text(
            """
            INSERT INTO knowledge (id, type, issue_id, summary, body, sources, source, created_at)
            VALUES (:id, :type, :issue_id, :summary,
                    CAST(:body AS jsonb), CAST(:sources AS jsonb), :source, :created_at)
            ON CONFLICT (id) DO UPDATE SET
                type = EXCLUDED.type,
                issue_id = EXCLUDED.issue_id,
                summary = EXCLUDED.summary,
                body = EXCLUDED.body,
                sources = EXCLUDED.sources,
                source = EXCLUDED.source
            """
        )
        async with pg.get_engine().begin() as conn:
            await conn.execute(
                query,
                {
                    "id": knowledge.id,
                    "type": knowledge.type,
                    "issue_id": knowledge.issue_id or None,  # 전문가 문서는 이슈 미연결 허용
                    "summary": knowledge.summary,
                    "body": json.dumps(knowledge.body),
                    "sources": json.dumps(list(knowledge.sources)),
                    "source": knowledge.source,
                    "created_at": knowledge.created_at,
                },
            )

    async def list_by_issue(self, issue_id: str) -> list[Knowledge]:
        query = text(
            "SELECT id, type, issue_id, summary, body, sources, source, created_at "
            "FROM knowledge WHERE issue_id = :iid ORDER BY created_at"
        )
        async with pg.get_engine().connect() as conn:
            rows = (await conn.execute(query, {"iid": issue_id})).all()
        return [_row_to_knowledge(row) for row in rows]

    async def get(self, knowledge_id: str) -> Knowledge | None:
        query = text(
            "SELECT id, type, issue_id, summary, body, sources, source, created_at "
            "FROM knowledge WHERE id = :id"
        )
        async with pg.get_engine().connect() as conn:
            row = (await conn.execute(query, {"id": knowledge_id})).first()
        return _row_to_knowledge(row) if row is not None else None


class PostgresIssueSourceReader(IssueSourceReader):
    """issues/comments/commits/events 를 조인해 스냅샷을 조립한다."""

    async def get_snapshot(self, issue_id: str) -> IssueSnapshot | None:
        async with pg.get_engine().connect() as conn:
            issue = (
                await conn.execute(
                    text(
                        "SELECT id, jira_key, summary, status, priority, "
                        "COALESCE(assignee, '') AS assignee, "
                        "COALESCE(reporter, '') AS reporter, "
                        "COALESCE(description, '') AS description, "
                        "labels, components FROM issues WHERE id = :id"
                    ),
                    {"id": issue_id},
                )
            ).first()
            if issue is None:
                return None
            comments = (
                await conn.execute(
                    text(
                        "SELECT body FROM comments WHERE issue_id = :id ORDER BY created_at"
                    ),
                    {"id": issue_id},
                )
            ).all()
            commits = (
                await conn.execute(
                    text(
                        "SELECT c.sha FROM commits c "
                        "JOIN issue_commits ic ON ic.commit_id = c.id "
                        "WHERE ic.issue_id = :id ORDER BY c.committed_at"
                    ),
                    {"id": issue_id},
                )
            ).all()
            events = (
                await conn.execute(
                    text(
                        "SELECT id FROM events WHERE payload->>'issue_id' = :id "
                        "ORDER BY occurred_at"
                    ),
                    {"id": issue_id},
                )
            ).all()
        return IssueSnapshot(
            issue_id=str(issue.id),
            jira_key=issue.jira_key,
            summary=issue.summary,
            status=issue.status,
            priority=issue.priority,
            comments=tuple(row.body for row in comments),
            commit_shas=tuple(row.sha for row in commits),
            source_event_ids=tuple(str(row.id) for row in events),
            assignee=issue.assignee,
            reporter=issue.reporter,
            description=issue.description,
            labels=tuple(issue.labels or ()),
            components=tuple(issue.components or ()),
        )


def _row_to_knowledge(row: object) -> Knowledge:
    # SQLAlchemy Row 는 속성 접근을 지원한다.
    return Knowledge(
        id=str(row.id),  # type: ignore[attr-defined]
        type=row.type,  # type: ignore[attr-defined]
        issue_id=str(row.issue_id) if row.issue_id else "",  # type: ignore[attr-defined]
        summary=row.summary,  # type: ignore[attr-defined]
        body=row.body,  # type: ignore[attr-defined]
        sources=tuple(row.sources),  # type: ignore[attr-defined]
        created_at=row.created_at,  # type: ignore[attr-defined]
        source=row.source,  # type: ignore[attr-defined]
    )
