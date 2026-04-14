import yaml
from pathlib import Path

CONFIG_PATH = "/etc/neron/server/neron.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_llm_config():
    return load_config().get("llm", {})
