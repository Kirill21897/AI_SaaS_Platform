from sqlalchemy import Column, Integer, String, Float, Boolean, Text
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base_class import Base

class Track(Base):
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=False)
    specialization = Column(String, index=True, nullable=False)
    region = Column(String, index=True, nullable=True)
    format = Column(String, index=True, nullable=True) # remote, office, hybrid
    
    min_gpa = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    
    # Store skill weights as JSON, e.g., {"python": 0.5, "sql": 0.3}
    required_skills = Column(JSONB, default={})
    tasks = Column(JSONB, default=[])
