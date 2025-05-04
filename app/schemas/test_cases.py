from pydantic import BaseModel
from typing import Optional, List

class TestCaseBase(BaseModel):
    input: str
    expected_output: str
    is_sample: bool = False
    is_hidden: bool = False
    order: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_kb: Optional[int] = None
    score: int = 100

class TestCaseCreate(TestCaseBase):
    pass

class TestCase(TestCaseBase):
    id: str
    problem_id: str
    
    class Config:
        from_attributes = True  # Thay thế cho orm_mode trong pydantic v2

class Message(BaseModel):
    message: str