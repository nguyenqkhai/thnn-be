import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.sql import func

from app.db.base_class import Base

class JudgeServer(Base):
    __tablename__ = "judge_servers"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    hostname = Column(String(100), nullable=False)
    port = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime, nullable=True)
    max_workers = Column(Integer, default=4)
    current_workers = Column(Integer, default=0)
    secret_key = Column(String(255), nullable=False)