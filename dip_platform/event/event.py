"""Event 원형 — DIP에서 역사와 지식의 원료.

계약: [.ai/contracts/event-contract.md]
- 이름은 과거형 PascalCase (`IssueCreated`).
- 페이로드는 불변 DTO(`<Event>Payload`), 식별자 + 필요한 최소 값.
- Event 는 append-only, 절대 덮어쓰지 않는다.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime


class EventPayload:
    """모든 이벤트 페이로드의 마커 베이스.

    구현체는 `@dataclass(frozen=True)` 로 불변을 보장한다.
    """


@dataclass(frozen=True)
class Event:
    """무슨 일이 있었다 — 불변 사실.

    Attributes:
        name: 과거형 PascalCase 이벤트명.
        payload: 불변 페이로드 DTO.
        event_id: 멱등 처리를 위한 고유 식별자.
        occurred_at: 발생 시각(UTC).
    """

    name: str
    payload: EventPayload
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# 핸들러는 하나의 Event 를 받아 자기 작업을 수행한다(멱등). 부수효과는 async I/O.
EventHandler = Callable[[Event], Awaitable[None]]
