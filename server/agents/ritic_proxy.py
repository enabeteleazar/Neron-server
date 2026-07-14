#!/usr/bin/env python3
import json
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("critic_proxy")

# --- Config ---
NERON_URL = "http://localhost:8010/input/text"

OLLAMA_URL = "http://localhost:11434/api/generate"
CRITIC_MODEL = "llama3.2:3b"  # ajuste selon NAME                     ID              SIZE      MODIFIED       
llama3.2:3b              a80c4f17acd5    2.0 GB    19 minutes ago    
qwen3:32b                030ee887880f    20 GB     14 hours ago      
glm-5.2:cloud            ce8fd6f94793    -         7 days ago        
kimi-k2.7-code:cloud     eda07a659237    -         3 weeks ago       
Qwen2.5-Coder:1.5b       d7372fd82851    986 MB    7 weeks ago       
gemma4:31b-cloud         c382fbfbc73b    -         8 weeks ago       
deepseek-v4-pro:cloud    22bfd5026abd    -         2 months ago      

FEEDBACK_LOG = Path.home() / "neron_feedback" / "feedback.jsonl"
FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)

CRITIC_PROMPT = """Tu évalues une réponse d'assistant IA.

Question: {question}
Réponse: {reponse}

Note sur 10 la pertinence et la justesse de la réponse.
Si le score est inférieur à 7, explique en 1-2 phrases ce qui ne va pas et propose une correction concise.

Réponds UNIQUEMENT en JSON valide, sans texte autour :
{{"score": <int>, "critique": "<string ou null>", "correction": "<string ou null>"}}"""


def load_env_var(key: str, env_file: str = "/srv/homelab/server-1/neronOS/secrets.env") -> str:
    with open(env_file) as f:
        for line in f:
            if line.startswith(f"{key}="):
                return line.strip().split("=", 1)[1]
    return ""


NERON_TOKEN = load_env_var("NERON_API_KEY")


async def call_neron(message: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            NERON_URL,
            json={"text": message},
            headers={"Authorization": f"Bearer {NERON_TOKEN}"},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")


async def call_critic(question: str, reponse: str) -> dict:
    prompt = CRITIC_PROMPT.format(question=question, reponse=reponse)
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(OLLAMA_URL, json={
            "model": CRITIC_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
        })
        resp.raise_for_status()
        raw = resp.json()["response"]
        return json.loads(raw)


def log_feedback(entry: dict):
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def critic_background(question: str, reponse: str):
    try:
        result = await call_critic(question, reponse)
    except Exception as e:
        logger.error(f"Critic failed: {type(e).__name__}: {e!r}")
        result = {"score": None, "critique": f"erreur: {type(e).__name__}", "correction": None}

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "reponse": reponse,
        **result,
    }
    log_feedback(entry)
    logger.info(f"Critic score: {entry.get('score')} — {entry.get('critique')}")


async def main(message: str):
    reponse = await call_neron(message)
    print(f"\nNéron: {reponse}\n")

    task = asyncio.create_task(critic_background(message, reponse))
    await task  # enlève cette ligne pour du vrai fire-and-forget sans attendre


TEST_MESSAGES = [
    "Quelle heure est-il ?",
    "C'est quoi la capitale de la France ?",
    "Explique-moi le protocole A2A",
    "Qu'est-ce qu'Oblivia et à quoi ça sert ?",
    "Comment fonctionne le lifecycle des prédicats dans ta mémoire ?",
    "Est-ce que tu te souviens de mon prénom ?",
    "Sur quoi je travaille en ce moment ?",
    "Fais quelque chose d'utile",
    "Aide-moi",
    "Donne-moi exactement 3 bullet points sur tes agents actifs, rien d'autre",
]


async def run_batch():
    for msg in TEST_MESSAGES:
        print(f"\n=== {msg} ===")
        try:
            await main(msg)
        except Exception as e:
            logger.error(f"Échec sur '{msg}': {e}")
        await asyncio.sleep(2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python critic_proxy.py "ton message"')
        print("  python critic_proxy.py --batch")
        sys.exit(1)

    if sys.argv[1] == "--batch":
        asyncio.run(run_batch())
    else:
        message = " ".join(sys.argv[1:])
        asyncio.run(main(message))

