import yaml
from pathlib import Path

CONFIG_PATH = "/etc/neron/server/neron.yaml"


def load_config() -> dict:
    path = Path(CONFIG_PATH)
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def get_llm_config() -> dict:
    return load_config().get("llm", {})
