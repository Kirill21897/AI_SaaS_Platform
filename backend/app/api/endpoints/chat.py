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
    base = settings.OLLAMA_BASE_URL.rstrip("/")
    try:
        version = httpx.get(f"{base}/api/version", timeout=5).json()
        show = httpx.post(f"{base}/api/show", json={"name": settings.OLLAMA_CHAT_MODEL}, timeout=15).json()
        return {
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "ollama_version": version.get("version"),
            "chat_model": settings.OLLAMA_CHAT_MODEL,
            "chat_model_loaded": bool(show.get("modelfile") or show.get("details") or show.get("modelinfo")),
        }
    except Exception as e:
        return {
            "ollama_base_url": settings.OLLAMA_BASE_URL,
            "chat_model": settings.OLLAMA_CHAT_MODEL,
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
