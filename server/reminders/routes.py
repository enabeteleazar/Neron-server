from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from reminders import db
from reminders.infra.security import require_api_key
from reminders.models import Reminder, ReminderCreate, ReminderUpdate

router = APIRouter(prefix="/reminders", dependencies=[Depends(require_api_key)])


@router.post("", response_model=Reminder, status_code=201)
async def create(payload: ReminderCreate) -> dict:
    return db.create_reminder(payload.model_dump())


@router.get("", response_model=list[Reminder])
async def list_all(status: str | None = None, limit: int = 100) -> list[dict]:
    return db.list_reminders(status_filter=status, limit=limit)


@router.get("/{reminder_id}", response_model=Reminder)
async def get_one(reminder_id: str) -> dict:
    reminder = db.get_reminder(reminder_id)
    if reminder is None:
        raise HTTPException(404, "Rappel introuvable")
    return reminder


@router.patch("/{reminder_id}", response_model=Reminder)
async def update(reminder_id: str, payload: ReminderUpdate) -> dict:
    existing = db.get_reminder(reminder_id)
    if existing is None:
        raise HTTPException(404, "Rappel introuvable")
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    return db.update_reminder(reminder_id, fields)  # type: ignore[return-value]


@router.delete("/{reminder_id}", status_code=204)
async def delete(reminder_id: str) -> None:
    if not db.delete_reminder(reminder_id):
        raise HTTPException(404, "Rappel introuvable")
