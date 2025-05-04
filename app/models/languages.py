import uuid
from sqlalchemy import Column, String, Boolean, Text, Float
from sqlalchemy.dialects.mysql import CHAR

from app.db.base_class import Base

class Language(Base):
    __tablename__ = "languages"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(50), nullable=False)
    identifier = Column(String(20), nullable=False, unique=True)
    compile_command = Column(Text, nullable=True)
    run_command = Column(Text, nullable=False)
    file_extension = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    time_limit_multiplier = Column(Float, default=1.0)
    memory_limit_multiplier = Column(Float, default=1.0)