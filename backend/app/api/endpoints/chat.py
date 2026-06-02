from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api import deps
from ai_engine.core.orchestrator import AIEngineOrchestrator
from ai_engine.memory.redis_store import RedisMemoryStore
from app.crud import crud_profile
from app.core.config import settings
import httpx
import re

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

def _normalize_session_suffix(value: str | None) -> str | None:
    if not value:
        return None
    suffix = value.strip()
    if not suffix:
        return None
    suffix = re.sub(r"[^a-zA-Z0-9_\-:.]", "", suffix)[:64]
    return suffix or None

def _make_session_id(user_id: int, x_session_id: str | None) -> str:
    suffix = _normalize_session_suffix(x_session_id)
    if not suffix:
        return str(user_id)
    return f"{user_id}:{suffix}"

@router.get("/health")
def chat_health():
    if settings.OPENROUTER_API_KEY is None or not settings.OPENROUTER_API_KEY.get_secret_value():
        return {
            "llm_provider": "openrouter",
            "chat_base_url": settings.OPENROUTER_BASE_URL,
            "chat_model": settings.OPENROUTER_MODEL,
            "embedding_model": settings.OPENROUTER_EMBEDDING_MODEL,
            "error": "OPENROUTER_API_KEY is not set",
        }

    chat_base = settings.OPENROUTER_BASE_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY.get_secret_value()}",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }
    try:
        models_resp = httpx.get(f"{chat_base}/models", headers=headers, timeout=15)
        models_resp.raise_for_status()
        models = models_resp.json().get("data") or []

        chat_model_available = any(model.get("id") == settings.OPENROUTER_MODEL for model in models)

        embedding_error = None
        embedding_ready = False
        try:
            embedding_resp = httpx.post(
                f"{chat_base}/embeddings",
                json={"model": settings.OPENROUTER_EMBEDDING_MODEL, "input": "ping"},
                headers=headers,
                timeout=30,
            )
            embedding_resp.raise_for_status()
            embedding_ready = True
        except Exception as exc:
            embedding_error = str(exc)

        return {
            "llm_provider": "openrouter",
            "chat_base_url": settings.OPENROUTER_BASE_URL,
            "chat_model": settings.OPENROUTER_MODEL,
            "chat_model_available": chat_model_available,
            "embedding_base_url": settings.OPENROUTER_BASE_URL,
            "embedding_model": settings.OPENROUTER_EMBEDDING_MODEL,
            "embedding_ready": embedding_ready,
            "embedding_error": embedding_error,
        }
    except Exception as e:
        return {
            "llm_provider": "openrouter",
            "chat_base_url": settings.OPENROUTER_BASE_URL,
            "chat_model": settings.OPENROUTER_MODEL,
            "error": str(e),
        }

@router.post("/stream")
async def chat_stream(
    msg: ChatMessage,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID")
):
    profile = crud_profile.get_profile_by_user_id(db, user_id=current_user.id)
    from app.db.redis import redis_client
    memory_store = RedisMemoryStore(redis_client)
    
    # We still need RecommendationEngine here for now as it's required by AIEngineOrchestrator
    from app.services.recommendation_engine import RecommendationEngine
    rec_engine = RecommendationEngine(db)
    
    agent = AIEngineOrchestrator(db, rec_engine, memory_store)
    session_id = _make_session_id(current_user.id, x_session_id)
    
    return StreamingResponse(
        agent.process_message(session_id, msg.message, profile),
        media_type="text/event-stream"
    )

@router.get("/state")
async def chat_state(
    current_user = Depends(deps.get_current_user),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID")
):
    from app.db.redis import redis_client
    memory_store = RedisMemoryStore(redis_client)
    session_id = _make_session_id(current_user.id, x_session_id)
    state = memory_store.get_session(session_id)
    history = state.get("history") if isinstance(state.get("history"), list) else []
    return {
        "session_id": session_id,
        "stage": state.get("stage"),
        "filters": state.get("filters") if isinstance(state.get("filters"), dict) else {},
        "last": state.get("last") if isinstance(state.get("last"), dict) else {},
        "history_count": len(history),
        "history_tail": history[-6:],
    }

@router.post("/reset")
async def chat_reset(
    current_user = Depends(deps.get_current_user),
    x_session_id: str | None = Header(default=None, alias="X-Session-ID")
):
    from app.db.redis import redis_client
    memory_store = RedisMemoryStore(redis_client)
    session_id = _make_session_id(current_user.id, x_session_id)
    memory_store.save_session(
        session_id,
        {
            "filters": {},
            "stage": "START",
            "history": [],
            "last": {"tool": None, "arguments": {}, "query": None, "offset": 0, "limit": 0},
        },
    )
    return {"ok": True, "session_id": session_id}
