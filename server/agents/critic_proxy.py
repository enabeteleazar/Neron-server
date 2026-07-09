#!/usr/bin/env python3
import json
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone
import httpx
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("critic_proxy")

NERON_URL = "http://localhost:8010/input/text"

OLLAMA_URL = "http://localhost:11434/api/generate"
CRITIC_MODEL = "llama3.2:3b"

FEEDBACK_LOG = Path.home() / "neron_feedback" / "feedback.jsonl"
FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)

CRITIC_PROMPT = """Tu évalues une réponse d'assistant IA.

Question: {question}
Réponse: {reponse}

Note sur 10 la pertinence et la justesse de la réponse.
Si le score est inférieur à 7, explique en 1-2 phrases ce qui ne va pas et propose une correction concise.

Réponds UNIQUEMENT en JSON valide, sans texte autour :
{{"score": <int>, "critique": "<string ou null>", "correction": "<string ou null>"}}"""


def load_env_var(key: str, env_file: str = "/etc/neronOS/secrets.env") -> str:
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
    """Call the critic model with robust JSON parsing."""
    prompt = CRITIC_PROMPT.format(question=question, reponse=reponse)
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": CRITIC_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Log the error and return a fallback result
            logger.error(f"Critic HTTP error: {e.response.status_code} - {e.response.text}")
            return {"score": None, "critique": f"http_error:{e.response.status_code}", "correction": None}
        except httpx.RequestError as e:
            logger.error(f"Critic request error: {e}")
            return {"score": None, "critique": f"request_error:{type(e).__name__}", "correction": None}

        raw = resp.json().get("response", "")
        # Try to parse JSON directly
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extract the first JSON-like object using regex
            # Look for { ... } pattern (non-greedy)
            match = re.search(r'\{[^{}]*\}', raw)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            # If still fails, return a default structure
            logger.error(f"Failed to parse critic response as JSON: {raw[:200]}")
            return {"score": None, "critique": "invalid_json", "correction": None}
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
    await task


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
