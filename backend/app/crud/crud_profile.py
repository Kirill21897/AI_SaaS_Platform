from sqlalchemy.orm import Session
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileUpdate
from fastapi.encoders import jsonable_encoder

def calculate_completeness_score(profile: Profile) -> int:
    score = 0
    total_weights = 100
    
    # Simple heuristic for completeness
    if profile.first_name and profile.last_name:
        score += 10
    if profile.about:
        score += 15
    if profile.specialty:
        score += 15
    if profile.skills and len(profile.skills) > 0:
        score += 20
    if profile.experience and len(profile.experience) > 0:
        score += 20
    if profile.education and len(profile.education) > 0:
        score += 10
    if profile.location or profile.employment_format:
        score += 10
        
    return min(score, total_weights)

def get_profile_by_user_id(db: Session, user_id: int) -> Profile:
    return db.query(Profile).filter(Profile.user_id == user_id).first()

def create_profile(db: Session, obj_in: ProfileCreate) -> Profile:
    obj_in_data = jsonable_encoder(obj_in)
    db_obj = Profile(**obj_in_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_profile(db: Session, db_obj: Profile, obj_in: ProfileUpdate) -> Profile:
    obj_data = jsonable_encoder(db_obj)
    update_data = obj_in.model_dump(exclude_unset=True)
    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj
