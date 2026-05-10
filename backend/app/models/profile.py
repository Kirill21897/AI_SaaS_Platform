from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Profile(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), unique=True, nullable=False)
    
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    about = Column(String, nullable=True)
    specialty = Column(String, nullable=True)
    location = Column(String, nullable=True)
    employment_format = Column(String, nullable=True)
    portfolio_link = Column(String, nullable=True)
    
    # Store complex lists/dicts as JSONB
    skills = Column(JSONB, default=[])
    education = Column(JSONB, default=[])
    experience = Column(JSONB, default=[])
    preferences = Column(JSONB, default={})

    user = relationship("User", back_populates="profile")
