"""EventBus 단위 테스트 — 디스패치, 핸들러 격리, 무핸들러 no-op."""

from __future__ import annotations

from dataclasses import dataclass

from dip_platform.event import Event, EventPayload, InMemoryEventBus


@dataclass(frozen=True)
class _Ping(EventPayload):
    value: int


async def test_publish_invokes_subscribed_handler() -> None:
    bus = InMemoryEventBus()
    seen: list[EventPayload] = []

    async def handler(event: Event) -> None:
        seen.append(event.payload)

    bus.subscribe("Pinged", handler)
    payload = _Ping(1)
    await bus.publish(Event("Pinged", payload))

    assert seen == [payload]


async def test_handler_failure_is_isolated() -> None:
    bus = InMemoryEventBus()
    order: list[str] = []

    async def bad(event: Event) -> None:
        order.append("bad")
        raise RuntimeError("boom")

    async def good(event: Event) -> None:
        order.append("good")

    bus.subscribe("X", bad)
    bus.subscribe("X", good)

    # 한 핸들러가 실패해도 publish 는 예외를 전파하지 않고 나머지를 실행한다.
    await bus.publish(Event("X", _Ping(0)))

    assert order == ["bad", "good"]


async def test_publish_with_no_handlers_is_noop() -> None:
    bus = InMemoryEventBus()
    await bus.publish(Event("Nothing", _Ping(0)))
