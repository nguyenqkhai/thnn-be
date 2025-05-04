from sqlalchemy import Column, String, Text, DateTime, Integer, Enum, Boolean, ForeignKey, func
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
from sqlalchemy.dialects.mysql import CHAR

class Problem(Base):
    __tablename__ = "problems"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    difficulty = Column(Enum('easy', 'medium', 'hard'), nullable=False)
    tags = Column(JSON, default=[])
    example_input = Column(Text, nullable=False)
    example_output = Column(Text, nullable=False)
    constraints = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(36), ForeignKey("users.id"))
    is_public = Column(Boolean, default=True)
    time_limit_ms = Column(Integer, default=1000)
    memory_limit_kb = Column(Integer, default=262144)

    # Relationships
    creator = relationship("User", back_populates="problems")
    test_cases = relationship("TestCase", back_populates="problem", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="problem")
    contests = relationship("ContestProblem", back_populates="problem")


class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(CHAR(36), primary_key=True)
    problem_id = Column(CHAR(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    input = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_sample = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    order = Column(Integer, nullable=False)
    # Thêm các trường này nếu chưa có
    time_limit_ms = Column(Integer, nullable=True)
    memory_limit_kb = Column(Integer, nullable=True)
    score = Column(Integer, default=100)
    
    problem = relationship("Problem", back_populates="test_cases")