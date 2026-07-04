from __future__ import annotations

import json
import logging
from pathlib import Path

from common.paths import NERON_WORKSPACE_DIR
from modules.events.event import Event
from modules.events.event_bus import event_bus
from modules.self_repair.diagnostic import diagnose_alert
from modules.self_repair.repair_planner import propose_repair

logger = logging.getLogger("neron.self_repair")

REPORT_DIR = NERON_WORKSPACE_DIR / "repairs"


async def handle_system_alert_for_repair(event: Event) -> None:
    payload = event.payload or {}

    try:
        diagnostic = diagnose_alert(payload)
        proposal = propose_repair(diagnostic)

        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        report = {
            "source_event_id": event.event_id,
            "source_event_type": event.type,
            "created_at": event.created_at.isoformat(),
            "alert": payload,
            "diagnostic": diagnostic,
            "proposal": proposal,
        }

        report_path = REPORT_DIR / f"repair_{event.event_id}.json"
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        logger.info(
            "repair_proposed event_id=%s report=%s title=%s",
            event.event_id,
            report_path,
            proposal.get("title"),
        )

        await event_bus.publish(Event(
            type="repair.proposed",
            source="self.repair",
            payload={
                "source_event_id": event.event_id,
                "report_path": str(report_path),
                "title": proposal.get("title"),
                "risk": proposal.get("risk"),
                "requires_human_approval": proposal.get("requires_human_approval", True),
            },
        ))

    except Exception as exc:
        logger.warning("self_repair_failed event_id=%s error=%s", event.event_id, exc)
