from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.crud import crud_profile
from app.services.recommendation_engine import RecommendationEngine
from typing import Optional

router = APIRouter()

# Mocking current user ID
def get_current_user_id() -> int:
    return 1

@router.get("/")
def get_recommendations(
    format: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    profile = crud_profile.get_profile_by_user_id(db, user_id=current_user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found. Please complete your profile first.")
        
    filters = {}
    if format:
        filters["format"] = format
    if region:
        filters["region"] = region
        
    engine = RecommendationEngine(db)
    recommendations = engine.recommend(profile, filters)
    
    # Format response
    response = []
    for rec in recommendations:
        track = rec["track"]
        response.append({
            "track_id": track.id,
            "title": track.title,
            "specialization": track.specialization,
            "description": track.description,
            "format": track.format,
            "scores": {
                "final_score": round(rec["final_score"], 2),
                "semantic_score": round(rec["semantic_score"], 2),
                "skill_score": round(rec["skill_score"], 2)
            },
            "explanation_data": rec["explanation_data"]
        })
        
    return response
