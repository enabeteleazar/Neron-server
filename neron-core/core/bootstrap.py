from core.config import settings
from core.logging import init_logger

logger = init_logger()

def main():
    logger.info(f"Bootstrapping Néron en {settings.ENV}")
    logger.info(f"API disponible sur {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Niveau de log : {settings.LOG_LEVEL}")

if __name__ == "__main__":
    main()
