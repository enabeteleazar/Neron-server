import httpx


class OllamaProvider:

    async def generate(self, message: str):
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral",
                    "prompt": message,
                    "stream": False
                }
            )

        data = response.json()
        return data.get("response", "") 
