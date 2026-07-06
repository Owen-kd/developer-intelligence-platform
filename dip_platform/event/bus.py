"""EventBus — 모듈 간 결합 없이 사실을 전파한다.

결정 배경: [.ai/decisions/ADR-003-eventbus.md]
- 초기: 인프로세스(in-memory) 비동기 디스패치.
- 이후: Redis/브로커 백엔드로 교체 가능하도록 인터페이스를 유지한다([APR-007]).
- 한 핸들러의 실패가 다른 핸들러를 막지 않는다(격리) + 실패 로깅.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict

from shared.logger import get_logger

from .event import Event, EventHandler
from .store import EventStore

_logger = get_logger("event.bus")


class EventBus(ABC):
    """이벤트 발행/구독의 추상 인터페이스(포트)."""

    @abstractmethod
    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """이벤트명에 핸들러를 등록한다."""

    @abstractmethod
    async def publish(self, event: Event) -> None:
        """이벤트를 등록된 모든 핸들러에 전달한다."""


class InMemoryEventBus(EventBus):
    """인프로세스 EventBus 구현.

    같은 프로세스 안에서 동기적 등록 / 비동기 디스패치.
    핸들러는 등록 순서대로 실행되며, 하나가 실패해도 나머지는 계속된다.
    """

    def __init__(self, store: EventStore | None = None) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._store = store

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    async def publish(self, event: Event) -> None:
        # 디스패치 전에 append-only 로 적재한다(있다면). 이벤트는 사실의 원료다.
        if self._store is not None:
            await self._store.append(event)

        handlers = list(self._handlers.get(event.name, ()))
        _logger.info(
            "event.published",
            name=event.name,
            event_id=event.event_id,
            handlers=len(handlers),
        )
        for handler in handlers:
            # 격리: 한 핸들러의 예외가 다른 핸들러를 막지 않는다.
            # (감사 로그는 platform/audit 도입 후 여기에 연결 — Sprint-08)
            try:
                await handler(event)
            except Exception as exc:  # noqa: BLE001 - 격리가 의도된 지점
                _logger.error(
                    "event.handler_failed",
                    name=event.name,
                    event_id=event.event_id,
                    handler=getattr(handler, "__name__", repr(handler)),
                    error=str(exc),
                )
