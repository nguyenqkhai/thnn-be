from sqlalchemy import Boolean, Column, String, Text, DateTime, Integer, func
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    bio = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    rating = Column(Integer, default=0)

    # Relationships
    problems = relationship("Problem", back_populates="creator")
    contests = relationship("Contest", back_populates="creator")
    submissions = relationship("Submission", back_populates="user")
    participations = relationship("ContestParticipant", back_populates="user")