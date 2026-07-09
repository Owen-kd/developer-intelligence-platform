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

    async def save_embedding(self, knowledge_id: str, embedding: list[float]) -> None:
        """지식 행에 벡터 임베딩을 채운다(pgvector) — ADR-009."""
        query = text(
            "UPDATE knowledge SET embedding = CAST(:emb AS vector) WHERE id = :id"
        )
        async with pg.get_engine().begin() as conn:
            await conn.execute(query, {"id": knowledge_id, "emb": _vector_literal(embedding)})

    async def link_related_wiki(self, issue_id: str, wiki_id: str, score: float) -> None:
        """이슈에 유사 위키를 관련지식으로 연결한다(멱등) — 루프3-Push."""
        query = text(
            """
            INSERT INTO issue_related_wiki (issue_id, wiki_id, score)
            VALUES (:iid, :wid, :score)
            ON CONFLICT (issue_id, wiki_id) DO UPDATE SET score = EXCLUDED.score
            """
        )
        async with pg.get_engine().begin() as conn:
            await conn.execute(query, {"iid": issue_id, "wid": wiki_id, "score": score})

    async def list_related_wikis(self, issue_id: str) -> list[tuple[Knowledge, float]]:
        """이슈에 연결된 관련 위키를 유사도 내림차순으로 조회한다."""
        query = text(
            """
            SELECT k.id, k.type, k.issue_id, k.summary, k.body, k.sources, k.source,
                   k.created_at, r.score
            FROM issue_related_wiki r JOIN knowledge k ON k.id = r.wiki_id
            WHERE r.issue_id = :iid ORDER BY r.score DESC
            """
        )
        async with pg.get_engine().connect() as conn:
            rows = (await conn.execute(query, {"iid": issue_id})).all()
        return [(_row_to_knowledge(row), float(row.score)) for row in rows]

    async def search_semantic(
        self,
        embedding: list[float],
        limit: int = 5,
        types: tuple[str, ...] = (),
        shelf_patterns: tuple[str, ...] = (),
    ) -> list[tuple[Knowledge, float]]:
        """질의 임베딩과 코사인 유사한 지식을 top-k 로 반환한다(유사도 내림차순).

        `types` 가 주어지면 해당 type 만 검색한다(예: ('wiki',)). 미임베딩 행은 제외된다.
        `shelf_patterns` 가 주어지면(접근제어, ADR-010) 지식이 속한 이슈의 서가(components)가
        패턴(ILIKE)에 하나라도 매칭될 때만 반환한다(연결 이슈 없으면 제외 = 기본 deny).
        """
        type_cond = "AND k.type = ANY(:types)" if types else ""
        shelf_cond = (
            "AND EXISTS (SELECT 1 FROM issues i, "
            "jsonb_array_elements_text(i.components) s "
            "WHERE i.id = k.issue_id AND s ILIKE ANY(:shelfpats))"
            if shelf_patterns
            else ""
        )
        query = text(
            f"""
            SELECT k.id, k.type, k.issue_id, k.summary, k.body, k.sources, k.source,
                   k.created_at, 1 - (k.embedding <=> CAST(:q AS vector)) AS score
            FROM knowledge k
            WHERE k.embedding IS NOT NULL {type_cond} {shelf_cond}
            ORDER BY k.embedding <=> CAST(:q AS vector)
            LIMIT :lim
            """
        )
        params: dict[str, object] = {"q": _vector_literal(embedding), "lim": limit}
        if types:
            params["types"] = list(types)
        if shelf_patterns:
            params["shelfpats"] = list(shelf_patterns)
        async with pg.get_engine().connect() as conn:
            rows = (await conn.execute(query, params)).all()
        return [(_row_to_knowledge(row), float(row.score)) for row in rows]


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


def _vector_literal(embedding: list[float]) -> str:
    """float 리스트를 pgvector 텍스트 리터럴 '[v1,v2,...]' 로 만든다(CAST ... AS vector 용)."""
    return "[" + ",".join(repr(float(value)) for value in embedding) + "]"


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
