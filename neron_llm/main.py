import uvicorn
from neron_llm.api.server import app  # noqa: F401  — exposé pour uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "neron_llm.main:app",
        host="0.0.0.0",
        port=8765,
        reload=False,
    )
