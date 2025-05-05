from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import uuid
from datetime import datetime
# Xóa dòng: from app.schemas.contests import ContestProblemDetail, RegistrationStatusResponse

class Contest(Base):
    __tablename__ = "contests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="contests")
    problems = relationship("ContestProblem", back_populates="contest", cascade="all, delete-orphan")
    participants = relationship("ContestParticipant", back_populates="contest", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="contest")


class ContestProblem(Base):
    __tablename__ = "contest_problems"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contest_id = Column(String(36), ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(String(36), ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, nullable=False)
    points = Column(Integer, default=100)

    contest = relationship("Contest", back_populates="problems")
    problem = relationship("Problem", back_populates="contests")


class ContestParticipant(Base):
    __tablename__ = "contest_participants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    contest_id = Column(String(36), ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    score = Column(Integer, default=0)

    contest = relationship("Contest", back_populates="participants")
    user = relationship("User", back_populates="participations")


class RegistrationRequest(Base):
    __tablename__ = "registration_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contest_id = Column(String(36), ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="pending")  # pending, approved, rejected

    user = relationship("User")
    contest = relationship("Contest")