from fastapi import FastAPI
from neron_llm.api.routes import router

app = FastAPI(title="Néron LLM Service")

app.include_router(router)
