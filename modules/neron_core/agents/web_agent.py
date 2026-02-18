# modules/neron_core/agents/web_agent.py

"""
WebAgent — Recherche web via SearXNG (self-hosted).
Interroge l'instance SearXNG interne et retourne
les résultats les plus pertinents sous forme structurée.
"""

import httpx
import os
from .base_agent import BaseAgent, AgentResult

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://neron_searxng:8080")
SEARXNG_TIMEOUT = float(os.getenv("SEARXNG_TIMEOUT", "10.0"))
SEARXNG_MAX_RESULTS = int(os.getenv("SEARXNG_MAX_RESULTS", "5"))


class WebAgent(BaseAgent):
    """
    Agent de recherche web.
    Utilise SearXNG en JSON pour récupérer des résultats
    et les formatter pour le synthesizer.
    """

    def __init__(self):
        super().__init__(name="web_agent")

    async def execute(self, query: str, **kwargs) -> AgentResult:
        """
        Lance une recherche SearXNG et retourne les résultats formatés.
        """
        self.logger.info(f"Recherche web pour : {query!r}")
        start = self._timer()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=5.0,
                    read=SEARXNG_TIMEOUT,
                    write=5.0,
                    pool=5.0
                )
            ) as client:
                response = await client.get(
                    f"{SEARXNG_URL}/search",
                    params={
                        "q": query,
                        "format": "json",
                        "language": "fr",
                        "safesearch": "0"
                    }
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return self._failure(
                "SearXNG timeout — service trop lent ou inaccessible",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.ConnectError:
            return self._failure(
                f"SearXNG inaccessible à {SEARXNG_URL}",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.HTTPStatusError as e:
            return self._failure(
                f"SearXNG erreur HTTP {e.response.status_code}",
                latency_ms=self._elapsed_ms(start)
            )
        except httpx.RequestError as e:
            return self._failure(
                f"Erreur réseau SearXNG : {str(e)}",
                latency_ms=self._elapsed_ms(start)
            )
        except Exception as e:
            return self._failure(
                f"Erreur inattendue WebAgent : {str(e)}",
                latency_ms=self._elapsed_ms(start)
            )

        results = data.get("results", [])
        latency = self._elapsed_ms(start)

        if not results:
            return self._failure(
                "Aucun résultat trouvé pour cette requête",
                latency_ms=latency
            )

        top_results = results[:SEARXNG_MAX_RESULTS]
        formatted = self._format_results(query, top_results)

        return self._success(
            content=formatted,
            metadata={
                "query": query,
                "total_results": len(results),
                "returned": len(top_results),
                "sources": [r.get("url", "") for r in top_results]
            },
            latency_ms=latency
        )

    def _format_results(self, query: str, results: list) -> str:
        """
        Transforme les résultats bruts en texte structuré
        exploitable par le LLM pour synthèse.
        """
        lines = [f"Résultats de recherche pour : « {query} »\n"]

        for i, result in enumerate(results, 1):
            title = result.get("title", "Sans titre")
            url = result.get("url", "")
            content = result.get("content", "Pas de description disponible")
            lines.append(f"[{i}] {title}")
            lines.append(f"    URL : {url}")
            lines.append(f"    {content}")
            lines.append("")

        return "\n".join(lines)
