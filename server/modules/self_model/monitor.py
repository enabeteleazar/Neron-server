from __future__ import annotations

import asyncio
import logging
import time

from modules.events.event import Event
from modules.events.event_bus import event_bus
from modules.self_model.self_model import get_self_model

logger = logging.getLogger("neron.self_monitor")


class SelfMonitor:
    def __init__(self) -> None:
        self.running = False
        self.last_check = 0.0
        self._reported: set[str] = set()

    async def start(self) -> None:
        if self.running:
            return

        self.running = True
        logger.info("SelfMonitor démarré")

        while self.running:
            try:
                await self._tick()
            except Exception as exc:
                logger.warning("SelfMonitor erreur: %s", exc)

            await asyncio.sleep(10)

    async def stop(self) -> None:
        self.running = False

    async def _publish_alert_once(self, key: str, payload: dict) -> None:
        if key in self._reported:
            return

        self._reported.add(key)

        await event_bus.publish(Event(
            type="system.alert",
            source="self.monitor",
            payload=payload,
        ))

    async def _tick(self) -> None:
        model = get_self_model()
        model.collect_runtime()
        data = model.to_dict()

        self.last_check = time.time()

        alerts = data.get("recent_alerts", [])
        failures = data.get("agents_failures", {})
        events_seen = data.get("events_seen", 0)
        runtime = data.get("runtime", {})

        logger.info(
            "SELF_MONITOR events=%s alerts=%s cpu=%s ram=%s disk=%s health=%s",
            events_seen,
            len(alerts),
            runtime.get("cpu_usage"),
            runtime.get("ram_usage"),
            runtime.get("disk_usage"),
            data.get("health_level"),
        )

        for agent, count in failures.items():
            if count >= 3:
                logger.warning(
                    "SELF_MONITOR anomaly=agent_instability agent=%s failures=%s",
                    agent,
                    count,
                )

                await self._publish_alert_once(
                    key=f"agent_instability:{agent}",
                    payload={
                        "level": "warning",
                        "reason": "agent_instability",
                        "agent": agent,
                        "failures": count,
                    },
                )

        if len(alerts) >= 5:
            logger.warning(
                "SELF_MONITOR anomaly=high_alert_volume count=%s",
                len(alerts),
            )

            await self._publish_alert_once(
                key="high_alert_volume",
                payload={
                    "level": "warning",
                    "reason": "high_alert_volume",
                    "alerts_count": len(alerts),
                },
            )

        if runtime.get("cpu_usage", 0) >= 90:
            await self._publish_alert_once(
                key="high_cpu",
                payload={
                    "level": "warning",
                    "reason": "high_cpu",
                    "cpu_usage": runtime.get("cpu_usage"),
                },
            )

        if runtime.get("ram_usage", 0) >= 90:
            await self._publish_alert_once(
                key="high_ram",
                payload={
                    "level": "warning",
                    "reason": "high_ram",
                    "ram_usage": runtime.get("ram_usage"),
                },
            )

        if runtime.get("disk_usage", 0) >= 90:
            await self._publish_alert_once(
                key="high_disk",
                payload={
                    "level": "warning",
                    "reason": "high_disk",
                    "disk_usage": runtime.get("disk_usage"),
                },
            )


_self_monitor: SelfMonitor | None = None


def get_self_monitor() -> SelfMonitor:
    global _self_monitor

    if _self_monitor is None:
        _self_monitor = SelfMonitor()

    return _self_monitor
