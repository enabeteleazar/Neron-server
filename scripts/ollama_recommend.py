#!/usr/bin/env python3
"""
scripts/ollama_recommend.py
Appelle llmfit et affiche les recommandations de modèles pour ce hardware.
Utilisé par `make ollama`.
"""

import json
import subprocess
import sys
from pathlib import Path

LLMFIT = Path(__file__).parent / "llmfit" / "llmfit.py"


def main():
    if not LLMFIT.exists():
        print("  ⚠️  llmfit non trouvé — utiliser la liste statique")
        sys.exit(1)

    try:
        result = subprocess.run(
            [sys.executable, str(LLMFIT), "recommend", "--limit", "5"],
            capture_output=True,
            text=True,
            timeout=30
        )
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"  ⚠️  llmfit échoué : {e}")
        sys.exit(1)

    s = data["system"]
    models = data["models"]

    print(f"  💻 Hardware détecté :")
    print(f"     CPU     : {s['cpu']}")
    print(f"     RAM     : {s['ram_gb']} GB disponible")
    print(f"     GPU     : {s['gpu'] or 'aucun'}")
    print(f"     Backend : {s['backend']}")
    print()
    print("  🏆 Modèles recommandés pour ce hardware :")
    print()

    for i, m in enumerate(models):
        short_name = m["name"].split("/")[-1]
        ollama_name = (
            short_name.lower()
            .replace("-instruct", "")
            .replace("-chat", "")
            .replace("-it", "")
        )
        fit_icon = {"Perfect": "🟢", "Good": "🟡", "Marginal": "🟠"}.get(m["fit"], "🔴")
        print(
            f"     {i+1}. {fit_icon} {short_name:<45}  score:{m['score']:>5}"
        )
    print()


if __name__ == "__main__":
    main()
