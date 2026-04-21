#!/usr/bin/env python3
"""
Script de migration pour chiffrer les secrets dans neron.yaml
Usage: python migrate_secrets.py
"""

import os
import yaml
from pathlib import Path
from cryptography.fernet import Fernet

# Générer une clé Fernet si elle n'existe pas
CIPHER_KEY_ENV = "NERON_CIPHER_KEY"
if not os.getenv(CIPHER_KEY_ENV):
    # Clé temporaire pour migration - À CHANGER EN PRODUCTION
    cipher_key = b'CHANGE_THIS_KEY_IN_PRODUCTION_32_BYTES_KEY'
    print(f"🔑 Clé de chiffrement temporaire: {cipher_key.decode()}")
    print(f"⚠️  DANGER: Changez cette clé en production!")
    os.environ[CIPHER_KEY_ENV] = cipher_key.decode()
else:
    cipher_key = os.getenv(CIPHER_KEY_ENV).encode()

cipher = Fernet(cipher_key)

# Charger neron.yaml
NERON_DIR = Path(__file__).parent
YAML_PATH = NERON_DIR / "neron.yaml"

if not YAML_PATH.exists():
    print("❌ neron.yaml non trouvé")
    exit(1)

with open(YAML_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f) or {}

# Secrets à chiffrer
secrets_paths = [
    ("neron", "api_key"),
    ("home_assistant", "token"),
    ("telegram", "bot_token"),
    ("watchdog", "bot_token"),
    ("twilio", "account_sid"),
    ("twilio", "auth_token"),
]

print("🔐 Chiffrement des secrets...")

for path in secrets_paths:
    current = config
    for key in path[:-1]:
        current = current.setdefault(key, {})
    secret_key = path[-1]

    print(f"Checking {'.'.join(path)}: {secret_key in current}")
    if secret_key in current and current[secret_key]:
        plain_value = current[secret_key]
        print(f"Value: {plain_value[:10]}...")
        if isinstance(plain_value, str):
            # Chiffrer si pas déjà chiffré (Fernet commence par gAAAAA)
            if not plain_value.startswith("gAAAAA"):
                encrypted = cipher.encrypt(plain_value.encode()).decode()
                current[secret_key] = encrypted
                print(f"✅ {'.'.join(path)} chiffré")
            else:
                print(f"⏭️  {'.'.join(path)} déjà chiffré")
        else:
            print(f"⏭️  {'.'.join(path)} n'est pas une string")

# Calculer hash SHA256 pour API_KEY
api_key = config.get("neron", {}).get("api_key", "")
if api_key and isinstance(api_key, str):
    import hashlib
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    print(f"🔒 Hash SHA256 de l'API_KEY: {api_key_hash}")
    print(f"⚠️  Définissez: export NERON_API_KEY_HASH={api_key_hash}")

# Sauvegarder
with open(YAML_PATH, "w", encoding="utf-8") as f:
    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

print("✅ Migration terminée. neron.yaml mis à jour avec secrets chiffrés.")
print(f"📁 Fichier sauvegardé: {YAML_PATH}")
print("🔄 Redémarrez le serveur après avoir défini les variables d'environnement.")