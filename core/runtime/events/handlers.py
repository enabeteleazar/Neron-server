def log_service_error(payload: dict):
    service = payload.get("service", "unknown")
    error = payload.get("error", "unknown")
    source = payload.get("source", "unknown")

    print(f"[EVENT] Erreur service détectée")
    print(f"Service : {service}")
    print(f"Erreur  : {error}")
    print(f"Source  : {source}")
