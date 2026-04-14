"""neronctl — CLI Néron LLM

Usage :
    python -m cli.neronctl "Qui es-tu ?" --task default --mode single
    python -m cli.neronctl "Compare ces deux approches" --mode parallel
    python -m cli.neronctl "Réponds vite" --mode race
"""
import asyncio
import json

import typer
from rich.console import Console
from rich.syntax import Syntax

from neron_llm.core.manager import LLMManager
from neron_llm.core.types import LLMRequest

app = typer.Typer(name="neronctl", help="Interface CLI pour le service LLM de Néron")
console = Console()
manager = LLMManager()


@app.command()
def chat(
    message: str = typer.Argument(..., help="Message à envoyer au LLM"),
    task: str = typer.Option("default", "--task", "-t", help="Tâche de routage (code, summary, default…)"),
    mode: str = typer.Option("single", "--mode", "-m", help="single | parallel | race"),
    provider: str = typer.Option(None, "--provider", "-p", help="Forcer un provider (ollama, claude)"),
    pretty: bool = typer.Option(False, "--pretty", help="Afficher la réponse en JSON formaté"),
):
    """Envoie un message au LLM et affiche la réponse."""
    req = LLMRequest(message=message, task=task, mode=mode, provider=provider)

    with console.status(f"[cyan]Appel LLM — mode={mode}…"):
        if mode == "parallel":
            result = asyncio.run(manager.generate_parallel(req))
        elif mode == "race":
            result = asyncio.run(manager.generate_race(req))
        else:
            result = asyncio.run(manager.generate(req))

    if pretty:
        payload = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
        console.print(Syntax(payload, "json", theme="monokai"))
    else:
        if mode == "parallel":
            for prov, resp in result.results.items():
                console.print(f"[bold cyan]{prov}[/bold cyan]: {resp}")
        elif mode == "race":
            console.print(f"[bold green]Gagnant: {result.winner}[/bold green]")
            console.print(result.response)
        else:
            console.print(f"[bold]{result.provider}[/bold] ({result.model}): {result.response}")


if __name__ == "__main__":
    app()
