from typing import Optional, List, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime

# TestCase schemas
class TestCaseBase(BaseModel):
    input: str
    expected_output: str
    is_sample: bool = False
    order: int
    time_limit_ms: Optional[int] = None
    memory_limit_kb: Optional[int] = None
    is_hidden: Optional[bool] = False
    score: Optional[int] = None

class TestCaseCreate(TestCaseBase):
    pass

class TestCaseUpdate(BaseModel):
    input: Optional[str] = None
    expected_output: Optional[str] = None
    is_sample: Optional[bool] = None
    order: Optional[int] = None
    time_limit_ms: Optional[int] = None
    memory_limit_kb: Optional[int] = None
    is_hidden: Optional[bool] = None
    score: Optional[int] = None
    
    class Config:
        from_attributes = True

class TestCaseInDBBase(TestCaseBase):
    id: str
    problem_id: str
    
    class Config:
        from_attributes = True

class TestCase(TestCaseInDBBase):
    pass

# Problem schemas
class ProblemBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Optional[Literal['easy', 'medium', 'hard']] = None
    tags: Optional[List[str]] = []
    example_input: Optional[str] = None
    example_output: Optional[str] = None
    constraints: Optional[str] = None
    is_public: Optional[bool] = True
    time_limit_ms: Optional[int] = 1000
    memory_limit_kb: Optional[int] = 262144
    
    @validator('title')
    def title_not_empty(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        return v
    
    @validator('description')
    def description_not_empty(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('Description cannot be empty')
        return v

class ProblemCreate(ProblemBase):
    title: str
    description: str
    difficulty: Literal['easy', 'medium', 'hard']
    example_input: str
    example_output: str
    constraints: str
    
class ProblemUpdate(ProblemBase):
    pass

class ProblemInDBBase(ProblemBase):
    id: str
    created_at: datetime
    created_by: Optional[str] = None
    
    class Config:
        from_attributes = True

class Problem(ProblemInDBBase):
    pass

class ProblemWithTestCases(Problem):
    test_cases: List[TestCase] = []