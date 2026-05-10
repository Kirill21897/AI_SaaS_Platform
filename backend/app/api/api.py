from fastapi import APIRouter
from app.api.endpoints import auth, profiles, tracks, chat

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(tracks.router, prefix="/tracks", tags=["tracks"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
