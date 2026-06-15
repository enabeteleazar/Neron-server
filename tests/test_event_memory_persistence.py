from __future__ import annotations

import sqlite3

from modules.events.event import Event


def test_persistent_store_migrates_incompatible_legacy_event_table(
    monkeypatch,
    tmp_path,
):
    from core.memory import persistent_store

    db_path = tmp_path / "memory.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                type TEXT,
                service TEXT,
                message TEXT,
                data TEXT
            )
            """
        )

    monkeypatch.setattr(persistent_store, "_DB_PATH", db_path)
    store = persistent_store.PersistentStore()
    event = Event(type="test.persisted", source="test", payload={"value": 1})

    row_id = store.push_event(
        event_id=event.event_id,
        event_type=event.type,
        source=event.source,
        payload=event.payload,
        created_at=event.created_at.isoformat(),
    )

    assert row_id > 0
    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(events)").fetchall()
        }
        backups = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name LIKE 'watchdog_events_legacy_%'"
        ).fetchall()
    assert "event_id" in columns
    assert len(backups) == 1
