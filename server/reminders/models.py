from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    content: str = Field(min_length=1)
    trigger_at: str
    source: str = "utilisateur"
    recurrence_rule: Optional[str] = None
    channel: Optional[str] = None
    metadata: Optional[str] = None


class ReminderUpdate(BaseModel):
    content: Optional[str] = None
    trigger_at: Optional[str] = None
    recurrence_rule: Optional[str] = None
    status: Optional[str] = None
    channel: Optional[str] = None
    metadata: Optional[str] = None


class Reminder(BaseModel):
    id: str
    content: str
    source: str
    trigger_at: str
    recurrence_rule: Optional[str] = None
    status: str
    channel: Optional[str] = None
    notified_at: Optional[str] = None
    notification_error: Optional[str] = None
    metadata: Optional[str] = None
    created_at: str
    triggered_at: Optional[str] = None
    dismissed_at: Optional[str] = None
