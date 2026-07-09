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

    async def consume_once(
        self, *, block_ms: int = 5000, count: int = 10, min_idle_ms: int = 60_000
    ) -> int:
        """스트림에서 한 배치를 처리한다(처리 수 반환).

        - 먼저 오래 미확인(pending)된 고아 메시지를 XAUTOCLAIM 으로 재청구·재처리한다
          (dispatch~ack 사이 크래시/재배포로 유실되지 않도록).
        - `_dispatch` 가 True(처리 성공/포이즌 드롭)일 때만 ack 한다. 핸들러가 실패하면
          ack 하지 않아 다음 사이클에 재전달된다(at-least-once; 핸들러는 멱등 전제).
        """
        processed = 0

        # 1) 고아 pending 재청구 (min_idle 초과분) — 신규만 읽는 '>' 의 사각을 보완
        try:
            claimed = await self._redis.xautoclaim(
                self._stream, self._group, self._consumer, min_idle_ms, start_id="0", count=count
            )
            messages = claimed[1] if isinstance(claimed, (list, tuple)) and len(claimed) > 1 else []
        except Exception as exc:  # xautoclaim 미지원/일시 오류는 신규 처리까지 막지 않는다
            _logger.warning("consume.reclaim_failed", error=str(exc))
            messages = []
        for message_id, fields in messages or []:
            if fields and await self._dispatch(fields):
                await self._redis.xack(self._stream, self._group, message_id)
                processed += 1

        # 2) 신규 메시지
        response = await self._redis.xreadgroup(
            self._group, self._consumer, {self._stream: ">"}, count=count, block=block_ms
        )
        for _stream_name, new_messages in response or []:
            for message_id, fields in new_messages:
                if await self._dispatch(fields):
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

    async def _dispatch(self, fields: dict[str, str]) -> bool:
        """메시지를 로컬 핸들러에 격리 디스패치. ack 해도 되는지(bool) 반환.

        - 파싱 불가(포이즌) 메시지는 로그 후 True(=ack, 드롭) — 재전달 크래시-루프 방지.
        - 핸들러가 하나라도 실패하면 False(=ack 안 함) — 재전달로 재시도(멱등 전제).
        """
        try:
            name = fields.get("name", "")
            payload_dict = json.loads(fields.get("payload", "{}"))
            event = Event(
                name=name,
                payload=_DictPayload(**payload_dict),
                event_id=fields.get("event_id", ""),
                occurred_at=_parse_dt(fields.get("occurred_at")),
            )
        except Exception as exc:  # 포이즌 메시지 → 드롭(ack) 하되 유실을 기록
            _logger.error("event.parse_failed", error=str(exc), raw=str(fields)[:200])
            return True

        all_ok = True
        for handler in list(self._handlers.get(name, ())):
            try:
                await handler(event)  # 격리: 한 핸들러 실패가 다른 핸들러를 막지 않는다
            except Exception as exc:
                all_ok = False  # 미ack → 재전달로 재시도
                _logger.error("event.handler_failed", name=name, error=str(exc))
        return all_ok
