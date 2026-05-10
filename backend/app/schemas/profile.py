from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Shared properties
class ProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    about: Optional[str] = None
    specialty: Optional[str] = None
    location: Optional[str] = None
    employment_format: Optional[str] = None
    portfolio_link: Optional[str] = None
    skills: Optional[List[str]] = []
    education: Optional[List[Dict[str, Any]]] = []
    experience: Optional[List[Dict[str, Any]]] = []
    preferences: Optional[Dict[str, Any]] = {}

# Properties to receive on item creation
class ProfileCreate(ProfileBase):
    # Make user_id optional since we will set it from current_user on the server
    user_id: Optional[int] = None

# Properties to receive on item update
class ProfileUpdate(ProfileBase):
    pass

# Properties to return to client
class ProfileInDBBase(ProfileBase):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

class ProfileResponse(ProfileInDBBase):
    completeness_score: int
