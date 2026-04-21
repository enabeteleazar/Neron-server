# neron-llm

# neron-llm

Microservice LLM unifié pour Néron. Abstrait les providers (Ollama, Claude) derrière une API FastAPI unique avec trois modes d'exécution.

## Modes

| Mode | Comportement |
|---|---|
| `single` | Un seul provider, sélectionné par le router |
| `parallel` | Tous les providers en `asyncio.gather` — tous les résultats |
| `race` | `asyncio.FIRST_COMPLETED` — le plus rapide gagne, les autres annulés |

## Structure

```
neron_llm/
├── config.py              # Lecture /etc/neron/server/neron.yaml
├── main.py                # Point d'entrée uvicorn
├── core/
│   ├── types.py           # LLMRequest / LLMResponse (Pydantic)
│   ├── router.py          # Routage tâche → modèle/provider
│   └── manager.py         # Orchestrateur async (single/parallel/race)
├── providers/
│   ├── base.py            # ABC async BaseProvider
│   ├── ollama.py          # Ollama via httpx async
│   └── claude.py          # Anthropic Claude via httpx async
└── api/
    └── server.py          # FastAPI app
cli/
└── neronctl.py            # CLI Typer
tests/
└── test_parallel.py       # Preuve du parallélisme
```

## Config neron.yaml

```yaml
llm:
  model: llama3.2:1b
  fallback_model: llama3.2:1b
  host: http://localhost:11434
  timeout: 120
  default_provider: ollama
  claude_api_key: sk-ant-...       # ou variable ANTHROPIC_API_KEY
  claude_max_tokens: 1024
  model_map:
    default: llama3.2:1b
    code: deepseek-coder:latest
    summary: llama3.2:1b
```

## Lancement

```bash
pip install -r requirements.txt
uvicorn neron_llm.main:app --host 0.0.0.0 --port 8765
```

## API

```
POST /chat
{
  "message": "Explique asyncio",
  "task": "default",
  "mode": "single",       # single | parallel | race
  "provider": null        # forcer ollama ou claude
}

GET /health
```

## CLI

```bash
python -m cli.neronctl "Qui es-tu ?" --mode single
python -m cli.neronctl "Compare ces approches" --mode parallel --pretty
python -m cli.neronctl "Réponds vite" --mode race
```

## Tests

```bash
pytest tests/ -v
