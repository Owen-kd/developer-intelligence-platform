"""Postgres 기반 EventStore — `events` 테이블에 append-only 적재.

인메모리 스토어와 같은 포트(`EventStore`)를 만족한다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime

from sqlalchemy import text

from dip_platform.event import Event, EventStore
from dip_platform.event.event import EventPayload

from . import connection as pg


def _payload_to_dict(payload: EventPayload) -> dict[str, object]:
    if is_dataclass(payload) and not isinstance(payload, type):
        return asdict(payload)
    return {}


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class PostgresEventStore(EventStore):
    """`events` 테이블에 이벤트를 적재/조회한다."""

    async def append(self, event: Event) -> None:
        query = text(
            """
            INSERT INTO events (id, name, payload, occurred_at)
            VALUES (:id, :name, CAST(:payload AS jsonb), :occurred_at)
            ON CONFLICT (id) DO NOTHING
            """
        )
        async with pg.get_engine().begin() as conn:
            await conn.execute(
                query,
                {
                    "id": event.event_id,
                    "name": event.name,
                    "payload": json.dumps(_payload_to_dict(event.payload)),
                    "occurred_at": event.occurred_at,
                },
            )

    async def list_by_name(self, name: str) -> list[Event]:
        query = text(
            "SELECT id, name, payload, occurred_at FROM events "
            "WHERE name = :name ORDER BY occurred_at"
        )
        async with pg.get_engine().connect() as conn:
            rows = (await conn.execute(query, {"name": name})).all()
        # 저장된 payload(jsonb)는 원형 dataclass 로 복원하지 않고 그대로 보존한다.
        return [
            Event(
                name=row.name,
                payload=EventPayload(),
                event_id=row.id,
                occurred_at=row.occurred_at,
            )
            for row in rows
        ]
