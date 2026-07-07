from memory.oblivia.manager import ObliviaMemoryManager
from memory.oblivia.schemas import MemoryRecord


_manager = None


class PersistentStoreAdapter:

    def __init__(self):
        self.memory = ObliviaMemoryManager(
            sqlite_path="memory/neron_memory.db"
        )

    def push_event(
        self,
        event_id,
        event_type,
        source,
        payload,
        created_at
    ):
        record = MemoryRecord(
            id=event_id,
            source=source,
            category=event_type,
            content=str(payload),
            metadata={
                "event": True
            },
            created_at=created_at
        )

        self.memory.remember(record)


_store = None


def get_store():
    global _store

    if _store is None:
        _store = PersistentStoreAdapter()

    return _store
