from sqlalchemy.orm import Session
from app.models.track import Track
from app.schemas.track import TrackCreate, TrackUpdate
from fastapi.encoders import jsonable_encoder

def get_track(db: Session, track_id: int):
    return db.query(Track).filter(Track.id == track_id).first()

def get_tracks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Track).filter(Track.is_active == True).offset(skip).limit(limit).all()

def create_track(db: Session, obj_in: TrackCreate):
    obj_in_data = jsonable_encoder(obj_in)
    db_obj = Track(**obj_in_data)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update_track(db: Session, db_obj: Track, obj_in: TrackUpdate):
    obj_data = jsonable_encoder(db_obj)
    update_data = obj_in.model_dump(exclude_unset=True)
    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete_track(db: Session, id: int):
    obj = db.query(Track).get(id)
    db.delete(obj)
    db.commit()
    return obj
