#!/usr/bin/env bash

set -e

SERVER_DIR="/etc/neron/server"

echo ""
echo "============================================"
echo "        CONFIG NERON (SAFE DISPLAY)"
echo "============================================"
echo ""

python3 - <<EOF
import yaml
from pathlib import Path

file = Path("${SERVER_DIR}/neron.yaml")

if not file.exists():
    print("❌ neron.yaml introuvable")
    exit(1)

data = yaml.safe_load(file.read_text())

SENSITIVE_KEYS = [
    "token",
    "api_key",
    "apikey",
    "secret",
    "password",
    "chat_id",
    "authorization"
]

def is_sensitive(key):
    k = key.lower()
    return any(s in k for s in SENSITIVE_KEYS)

def mask(value):
    if value is None:
        return value
    s = str(value)
    if len(s) <= 4:
        return "****"
    return "****" + s[-4:]

def clean(obj):
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if is_sensitive(k):
                new[k] = "[HIDDEN]"
            else:
                new[k] = clean(v)
        return new
    elif isinstance(obj, list):
        return [clean(x) for x in obj]
    else:
        return obj

cleaned = clean(data)

print(yaml.dump(cleaned, sort_keys=False, allow_unicode=True))
EOF

echo ""
echo "============================================"
