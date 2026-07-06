"""EventStore — 발행된 Event 를 불변(append-only)으로 적재하는 포트.

Timeline/Knowledge 승격의 원료가 된다([.ai/architecture/knowledge-lifecycle.md]).
구현: 인메모리(테스트/데모) · Postgres(`infrastructure/postgres/event_store.py`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .event import Event


class EventStore(ABC):
    """Event 를 append-only 로 적재하는 추상 저장소."""

    @abstractmethod
    async def append(self, event: Event) -> None:
        """Event 하나를 적재한다. 덮어쓰지 않는다."""

    @abstractmethod
    async def list_by_name(self, name: str) -> list[Event]:
        """이름으로 적재된 Event 를 발생 순으로 조회한다."""


class InMemoryEventStore(EventStore):
    """프로세스 메모리 기반 EventStore(테스트/데모용)."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    async def append(self, event: Event) -> None:
        self._events.append(event)

    async def list_by_name(self, name: str) -> list[Event]:
        return [event for event in self._events if event.name == name]

    @property
    def events(self) -> list[Event]:
        """적재된 모든 Event(발행 순)."""
        return list(self._events)
