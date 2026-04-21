# modules/neron_core/conftest.py
# Execute EN PREMIER par pytest - configure le sys.path avant tout import

import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print(f"[conftest] ROOT ajoute au path : {ROOT}")
