# agents/web_agent.py
import httpx
import os
from agents.base_agent import BaseAgent, AgentResult

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://neron_searxng:8080")
SEARXNG_TIMEOUT = float(os.getenv("SEARXNG_TIMEOUT", "10.0"))
SEARXNG_MAX_RESULTS = int(os.getenv("SEARXNG_MAX_RESULTS", "5"))


class WebAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="web_agent")

    async def execute(self, query: str, **kwargs) -> AgentResult:
        self.logger.info("Recherche web pour : " + repr(query))
        start = self._timer()

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(connect=5.0, read=SEARXNG_TIMEOUT, write=5.0, pool=5.0)
            ) as client:
                response = await client.get(
                    f"{SEARXNG_URL}/search",
                    params={"q": query, "format": "json", "language": "fr", "safesearch": "0"}
                )
                response.raise_for_status()
                data = response.json()

        except httpx.TimeoutException:
            return self._failure("searxng timeout", latency_ms=self._elapsed_ms(start))
        except httpx.ConnectError:
            return self._failure(f"searxng inaccessible a {SEARXNG_URL}", latency_ms=self._elapsed_ms(start))
        except httpx.HTTPStatusError as e:
            return self._failure(f"searxng erreur HTTP {e.response.status_code}", latency_ms=self._elapsed_ms(start))
        except httpx.RequestError as e:
            return self._failure(f"erreur reseau searxng : {str(e)}", latency_ms=self._elapsed_ms(start))
        except Exception as e:
            return self._failure(f"erreur inattendue : {str(e)}", latency_ms=self._elapsed_ms(start))

        results = data.get("results", [])
        latency = self._elapsed_ms(start)

        if not results:
            return self._failure("Aucun resultat trouve", latency_ms=latency)

        top = results[:SEARXNG_MAX_RESULTS]
        content = self._format(query, top)

        return self._success(
            content=content,
            metadata={
                "query": query,
                "total_results": len(results),
                "returned": len(top),
                "sources": [r.get("url", "") for r in top]
            },
            latency_ms=latency
        )

    def _format(self, query: str, results: list) -> str:
        lines = ["Resultats pour : " + query + "\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', 'Sans titre')}")
            lines.append(f"    URL : {r.get('url', '')}")
            lines.append(f"    {r.get('content', '')}")
            lines.append("")
        return "\n".join(lines)
