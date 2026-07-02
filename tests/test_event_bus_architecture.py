from __future__ import annotations

import pytest

from modules.events.event import Event
from modules.events.event_bus import EventBus


@pytest.mark.asyncio
async def test_publish_without_listener_is_a_noop():
    bus = EventBus()

    await bus.publish(Event(type="test.unobserved", payload={}))


@pytest.mark.asyncio
async def test_failing_listener_does_not_block_other_consumers():
    bus = EventBus()
    received = []

    async def failing_listener(_event):
        raise RuntimeError("listener failed")

    def healthy_listener(event):
        received.append(event.payload["value"])

    bus.subscribe("test.event", failing_listener)
    bus.subscribe("test.event", healthy_listener)

    await bus.publish(Event(type="test.event", payload={"value": 42}))

    assert received == [42]


@pytest.mark.asyncio
async def test_wildcard_listener_receives_dynamic_event_types():
    bus = EventBus()
    received = []

    bus.subscribe("*", received.append)

    await bus.publish(Event(type="watchdog.dynamic_alert", payload={"value": 1}))

    assert [event.type for event in received] == ["watchdog.dynamic_alert"]


def test_subscriptions_are_idempotent_and_removable():
    bus = EventBus()

    async def listener(_event):
        return None

    bus.subscribe("test.event", listener)
    bus.subscribe("test.event", listener)

    assert len(bus._subscribers["test.event"]) == 1
    assert bus.unsubscribe("test.event", listener) is True
    assert bus.unsubscribe("test.event", listener) is False


@pytest.mark.asyncio
async def test_memory_save_emits_update_after_persistence(monkeypatch, tmp_path):
    from agents.builtin.core import memory_agent
    from core.providers.memory import ObliviaProvider
    from core.providers.registry import ProviderRegistry
    from memory.oblivia import ObliviaMemoryManager

    registry = ProviderRegistry()
    registry.register(ObliviaProvider(ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )))
    monkeypatch.setattr(memory_agent, "provider_registry", registry)
    emitted = []

    async def capture(event):
        emitted.append(event)

    monkeypatch.setattr(memory_agent.event_bus, "publish", capture)

    row_id = await memory_agent.MemoryAgent().save(
        "question",
        "response",
        {"source": "test"},
    )

    assert row_id
    assert emitted[0].type == "memory.updated"
    assert emitted[0].payload["record_id"] == row_id


def test_world_model_emits_compact_observation_event(monkeypatch):
    from core.world_model import world_model

    emitted = []
    monkeypatch.setattr(
        world_model.event_bus,
        "publish_background",
        emitted.append,
    )

    model = world_model.WorldModel()
    model.update("agents", "memory", {"status": "online"})

    assert emitted[0].type == "world_model.observation_updated"
    assert emitted[0].payload["category"] == "agents"
    assert emitted[0].payload["key"] == "memory"
