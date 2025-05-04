from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from app.schemas.problems import ProblemBase
from app.schemas.users import UserBase
from app.schemas.contests import ContestBase
from app.schemas.test_cases import TestCaseBase

class SubmissionBase(BaseModel):
    problem_id: str
    code: str
    language: Literal['c', 'cpp', 'python', 'pascal']
    contest_id: Optional[str] = None

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionUpdate(BaseModel):
    status: Optional[Literal[
        'pending',
        'accepted',
        'wrong_answer',
        'time_limit_exceeded',
        'memory_limit_exceeded',
        'runtime_error',
        'compilation_error',
        'judge_error'  # Thêm giá trị này
    ]] = None
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None

class SubmissionInDBBase(SubmissionBase):
    id: str
    user_id: str
    status: Literal[
        'pending',
        'accepted',
        'wrong_answer',
        'time_limit_exceeded',
        'memory_limit_exceeded',
        'runtime_error',
        'compilation_error'
    ] = 'pending'
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    submitted_at: datetime
    
    class Config:
        from_attributes = True  # Thay thế cho orm_mode trong pydantic v2

class Submission(SubmissionInDBBase):
    pass

class SubmissionWithDetails(Submission):
    problem_title: Optional[str] = None
    username: Optional[str] = None

# Thêm model mới cho việc test code
class SubmissionTestInput(BaseModel):
    problem_id: str
    code: str
    language: Literal['c', 'cpp', 'python', 'pascal']
    input: str

class SubmissionTestResult(BaseModel):
    output: str
    status: str = "success"  # Mặc định là success
    execution_time_ms: Optional[int] = None
    memory_used_kb: Optional[int] = None
    message: Optional[str] = None

    class Config:
        from_attributes = True

class SubmissionDetails(BaseModel):
    total_test_cases: int
    passed_test_cases: int
    failed_test_cases: int
    test_results: List[SubmissionTestResult]
    error: Optional[str] = None

class Submission(SubmissionInDBBase):
    details: Optional[SubmissionDetails] = None