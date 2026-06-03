from core.runtime.events.event_bus import event_bus


async def emit_service_error(service: str, error: str, source: str = "unknown"):
    return await event_bus.emit(
        "system.service.error",
        {
            "service": service,
            "error": error,
            "source": source,
        },
    )
