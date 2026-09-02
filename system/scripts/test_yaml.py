import os

import yaml
from pathlib import Path

p = Path(os.getenv("NERON_CONFIG", "/etc/neronOS/neron.yaml"))
try:
    yaml.safe_load(p.read_text())
    print("YAML OK")
except Exception as e:
    print("YAML ERROR:")
    print(e)
