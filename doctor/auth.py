# app/auth.py
# Authentification par API Key (header X-Doctor-Key)

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from doctor.config import cfg

api_key_header = APIKeyHeader(name="X-Doctor-Key", auto_error=False)


def require_api_key(key: str = Security(api_key_header)):
    """
    Dependency FastAPI.
    Si DOCTOR_API_KEY est vide dans .env, l'auth est désactivée (dev mode).
    En production, la clé doit correspondre exactement.
    """
    if not cfg.API_KEY:
        return  # Auth désactivée

    if key != cfg.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set X-Doctor-Key header.",
        )
