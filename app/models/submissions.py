from sqlalchemy import Column, String, Text, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
from sqlalchemy.dialects.mysql import CHAR

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(CHAR(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    contest_id = Column(CHAR(36), ForeignKey("contests.id", ondelete="CASCADE"), nullable=True)
    code = Column(Text, nullable=False)
    language = Column(Enum('c', 'cpp', 'python', 'pascal'), nullable=False)
    status = Column(Enum(
        'pending',
        'accepted',
        'wrong_answer', 
        'time_limit_exceeded',
        'memory_limit_exceeded',
        'runtime_error',
        'compilation_error'
    ), nullable=False, default='pending')
    execution_time_ms = Column(Integer, nullable=True)
    memory_used_kb = Column(Integer, nullable=True)
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    contest = relationship("Contest", back_populates="submissions")
    test_results = relationship("SubmissionTestResult", back_populates="submission", cascade="all, delete-orphan")

class SubmissionTestResult(Base):
    __tablename__ = "submission_test_results"

    id = Column(CHAR(36), primary_key=True)
    submission_id = Column(CHAR(36), ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    test_case_id = Column(CHAR(36), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(
        "accepted",
        "wrong_answer",
        "time_limit_exceeded",
        "memory_limit_exceeded",
        "runtime_error",
        "compilation_error",
        "judge_error"
    ), nullable=False)
    execution_time_ms = Column(Integer, nullable=False)
    memory_used_kb = Column(Integer, nullable=False)
    output_diff = Column(Text, nullable=True)
    
    submission = relationship("Submission", back_populates="test_results")
    test_case = relationship("TestCase")