"""Redis Streams 기반 EventBus 어댑터 — 다중 프로세스 상시 구동(ADR-011).

`EventBus` 포트(dip_platform)를 구현한다(PostgresEventStore 와 동일한 포트-어댑터 선례).
- 발행: `XADD` 로 스트림에 적재(영속). `store` 주입 시 발행 전에 append-only 적재.
- 소비: `XREADGROUP`(소비자 그룹 + ack) → 로컬 핸들러에 격리 디스패치.
- 소비 측 payload 는 일반 객체(속성 접근)로 복원한다(핸들러가 getattr 규약을 씀).

한 핸들러 실패가 다른 핸들러를 막지 않는다(InMemoryEventBus 와 동일 계약).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime

import redis.asyncio as aioredis

from dip_platform.event import Event, EventBus, EventHandler, EventPayload, EventStore
from shared.logger import get_logger

_logger = get_logger("infra.redis.bus")

_STREAM = "dip:events"
_GROUP = "dip-workers"


class _DictPayload(EventPayload):
    """소비 측에서 복원한 일반 페이로드 — 핸들러는 속성(getattr)으로 접근한다."""

    def __init__(self, **fields: object) -> None:
        self.__dict__.update(fields)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(UTC)
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(UTC)


class RedisEventBus(EventBus):
    """Redis Streams 로 프로세스 간 이벤트를 전달하는 EventBus."""

    def __init__(
        self,
        url: str,
        *,
        stream: str = _STREAM,
        group: str = _GROUP,
        consumer: str = "worker-1",
        store: EventStore | None = None,
    ) -> None:
        self._redis = aioredis.from_url(url, decode_responses=True)
        self._stream = stream
        self._group = group
        self._consumer = consumer
        self._store = store
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        self._handlers[event_name].append(handler)

    async def publish(self, event: Event) -> None:
        if self._store is not None:
            await self._store.append(event)  # 발행 전 append-only 적재(사실의 원료)
        payload = (
            asdict(event.payload) if is_dataclass(event.payload) else dict(vars(event.payload))
        )
        await self._redis.xadd(
            self._stream,
            {
                "name": event.name,
                "event_id": event.event_id,
                "occurred_at": event.occurred_at.isoformat(),
                "payload": json.dumps(payload, ensure_ascii=False, default=str),
            },
        )
        _logger.info("event.published", name=event.name, event_id=event.event_id)

    async def ensure_group(self) -> None:
        """소비자 그룹을 생성한다(이미 있으면 무시)."""
        try:
            await self._redis.xgroup_create(self._stream, self._group, id="0", mkstream=True)
        except Exception as exc:  # BUSYGROUP = 이미 존재 → 정상
            if "BUSYGROUP" not in str(exc):
                raise

    async def consume_once(self, *, block_ms: int = 5000, count: int = 10) -> int:
        """스트림에서 한 배치를 읽어 로컬 핸들러에 디스패치·ack. 처리한 이벤트 수 반환."""
        response = await self._redis.xreadgroup(
            self._group, self._consumer, {self._stream: ">"}, count=count, block=block_ms
        )
        processed = 0
        for _stream_name, messages in response or []:
            for message_id, fields in messages:
                await self._dispatch(fields)
                await self._redis.xack(self._stream, self._group, message_id)
                processed += 1
        return processed

    async def run(self) -> None:
        """상시 소비 루프(worker 진입점) — target-service #4/#5."""
        await self.ensure_group()
        _logger.info("consumer.started", stream=self._stream, group=self._group)
        while True:
            await self.consume_once()

    async def aclose(self) -> None:
        await self._redis.aclose()

    async def _dispatch(self, fields: dict[str, str]) -> None:
        name = fields.get("name", "")
        payload_dict = json.loads(fields.get("payload", "{}"))
        event = Event(
            name=name,
            payload=_DictPayload(**payload_dict),
            event_id=fields.get("event_id", ""),
            occurred_at=_parse_dt(fields.get("occurred_at")),
        )
        for handler in list(self._handlers.get(name, ())):
            try:
                await handler(event)  # 격리: 한 핸들러 실패가 다른 핸들러를 막지 않는다
            except Exception as exc:
                _logger.error("event.handler_failed", name=name, error=str(exc))
