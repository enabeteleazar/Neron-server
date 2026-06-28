from __future__ import annotations

import requests
import yaml


CONFIG_PATH = "/etc/neron/neron.yaml"
NERON_API = "http://localhost:8010/cognitive-core/report"


def load_config() -> dict:
    with open(
        CONFIG_PATH,
        "r",
        encoding="utf-8",
    ) as f:
        return yaml.safe_load(f) or {}


CONFIG = load_config()

TELEGRAM_CONFIG = CONFIG.get(
    "telegram",
    {},
)

TELEGRAM_TOKEN = TELEGRAM_CONFIG.get(
    "bot_token"
)

TELEGRAM_CHAT_ID = TELEGRAM_CONFIG.get(
    "chat_id"
)


def get_report() -> str:
    response = requests.get(
        NERON_API,
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    return payload.get(
        "report",
        "Rapport indisponible.",
    )


def send_telegram_message(
    text: str,
) -> None:

    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN manquant"
        )

    if not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID manquant"
        )

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
        },
        timeout=30,
    )

    response.raise_for_status()


def main() -> None:
    report = get_report()

    send_telegram_message(
        report
    )

    print(
        "Rapport Telegram envoyé."
    )


if __name__ == "__main__":
    main()
