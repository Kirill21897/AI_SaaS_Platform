from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.api import deps
from app.services.agent import AgentOrchestrator
from app.crud import crud_profile

router = APIRouter()

class ChatMessage(BaseModel):
    message: str

@router.post("/stream")
async def chat_stream(
    msg: ChatMessage,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
):
    profile = crud_profile.get_profile_by_user_id(db, user_id=current_user.id)
    agent = AgentOrchestrator(db)
    
    return StreamingResponse(
        agent.process_message(current_user.id, msg.message, profile),
        media_type="text/event-stream"
    )
