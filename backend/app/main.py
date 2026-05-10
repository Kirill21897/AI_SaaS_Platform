import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.api import api_router
from app.db.base_class import Base
from app.db.session import engine
import app.models  # This imports the models so metadata can find them
import httpx

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def warmup_ollama():
    async def _warm():
        base = settings.OLLAMA_BASE_URL.rstrip("/")
        options: dict = {
            "num_ctx": settings.OLLAMA_NUM_CTX,
            "num_predict": settings.OLLAMA_NUM_PREDICT,
            "temperature": settings.OLLAMA_TEMPERATURE,
            "top_p": settings.OLLAMA_TOP_P,
            "repeat_penalty": settings.OLLAMA_REPEAT_PENALTY,
        }
        options = {k: v for k, v in options.items() if v is not None}
        payload = {
            "model": settings.OLLAMA_CHAT_MODEL,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
        }
        if options:
            payload["options"] = options

        async with httpx.AsyncClient(timeout=120) as client:
            for attempt in range(6):
                try:
                    await client.post(
                        f"{base}/api/embeddings",
                        json={"model": settings.OLLAMA_EMBEDDING_MODEL, "prompt": "ping"},
                    )
                    await client.post(f"{base}/api/chat", json=payload)
                    return
                except Exception:
                    await asyncio.sleep(min(2**attempt, 20))

    asyncio.create_task(_warm())

@app.get("/health")
def health_check():
    return {"status": "ok"}
