from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.crud import crud_profile
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=ProfileResponse)
def read_profile_me(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    profile = crud_profile.get_profile_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    score = crud_profile.calculate_completeness_score(profile)
    
    # Add calculated score dynamically for response
    profile_dict = profile.__dict__
    profile_dict["completeness_score"] = score
    
    return profile_dict

@router.post("/", response_model=ProfileResponse)
def create_profile(
    profile_in: ProfileCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    # Ensure users can only create profiles for themselves
    if profile_in.user_id != current_user.id:
        profile_in.user_id = current_user.id

    profile = crud_profile.get_profile_by_user_id(db, user_id=current_user.id)
    if profile:
        raise HTTPException(status_code=400, detail="Profile already exists for this user")
    
    profile = crud_profile.create_profile(db=db, obj_in=profile_in)
    score = crud_profile.calculate_completeness_score(profile)
    
    profile_dict = profile.__dict__
    profile_dict["completeness_score"] = score
    return profile_dict

@router.put("/me", response_model=ProfileResponse)
def update_profile_me(
    profile_in: ProfileUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    profile = crud_profile.get_profile_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    profile = crud_profile.update_profile(db=db, db_obj=profile, obj_in=profile_in)
    score = crud_profile.calculate_completeness_score(profile)
    
    profile_dict = profile.__dict__
    profile_dict["completeness_score"] = score
    return profile_dict
