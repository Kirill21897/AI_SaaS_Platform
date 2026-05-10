from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TrackBase(BaseModel):
    title: str
    description: str
    specialization: str
    region: Optional[str] = None
    format: Optional[str] = None
    min_gpa: Optional[float] = 0.0
    is_active: Optional[bool] = True
    required_skills: Optional[Dict[str, float]] = {}
    tasks: Optional[List[str]] = []

class TrackCreate(TrackBase):
    pass

class TrackUpdate(TrackBase):
    title: Optional[str] = None
    description: Optional[str] = None
    specialization: Optional[str] = None

class TrackResponse(TrackBase):
    id: int

    class Config:
        from_attributes = True
