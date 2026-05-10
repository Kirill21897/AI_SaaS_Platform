from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.crud import crud_user

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_user(db: Session = Depends(get_db)) -> User:
    # MOCK AUTH for AI Assistant development phase
    user = crud_user.get_by_id(db, id=1)
    if not user:
        user = User(email="mock@example.com", hashed_password="mock")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
