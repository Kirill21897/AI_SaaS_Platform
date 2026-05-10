from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.track import TrackCreate, TrackUpdate, TrackResponse
from app.crud import crud_track

router = APIRouter()

@router.get("/", response_model=List[TrackResponse])
def read_tracks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    tracks = crud_track.get_tracks(db, skip=skip, limit=limit)
    return tracks

@router.get("/{track_id}", response_model=TrackResponse)
def read_track(
    track_id: int,
    db: Session = Depends(get_db)
):
    track = crud_track.get_track(db, track_id=track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track

@router.post("/", response_model=TrackResponse)
def create_track(
    track_in: TrackCreate,
    db: Session = Depends(get_db)
):
    track = crud_track.create_track(db, obj_in=track_in)
    return track

@router.put("/{track_id}", response_model=TrackResponse)
def update_track(
    track_id: int,
    track_in: TrackUpdate,
    db: Session = Depends(get_db)
):
    track = crud_track.get_track(db, track_id=track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    track = crud_track.update_track(db, db_obj=track, obj_in=track_in)
    return track

@router.delete("/{track_id}", response_model=TrackResponse)
def delete_track(
    track_id: int,
    db: Session = Depends(get_db)
):
    track = crud_track.get_track(db, track_id=track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return crud_track.delete_track(db, id=track_id)
