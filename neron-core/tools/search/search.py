import httpx
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

SEARXNG_URL = "http://neron-searxng:8080"

async def web_search(query: str, num_results: int = 5) -> List[Dict]:
    """
    Recherche web via SearXNG
    
    Args:
        query: Requête de recherche
        num_results: Nombre de résultats (max)
        
    Returns:
        Liste de résultats [{title, url, content}]
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SEARXNG_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": "fr"
                },
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", "")[:200]
                })
            
            logger.info(f"Found {len(results)} results for: {query}")
            return results
            
    except httpx.TimeoutException:
        logger.error("Search timeout")
        return []
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def format_search_results(results: List[Dict]) -> str:
    """
    Formate les résultats pour le LLM
    """
    if not results:
        return "Aucun résultat trouvé."
    
    formatted = "Résultats de recherche :\n\n"
    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result['title']}\n"
        formatted += f"   URL: {result['url']}\n"
        if result['content']:
            formatted += f"   {result['content']}\n"
        formatted += "\n"
    
    return formatted
