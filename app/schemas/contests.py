from typing import Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
from app.schemas.problems import Problem
# Xóa dòng: from app.schemas.contests import RegistrationStatusResponse

# ContestProblem schemas
class ContestProblemBase(BaseModel):
    problem_id: str
    order: int
    points: Optional[int] = 100

class ContestProblemCreate(ContestProblemBase):
    pass

class ContestProblemUpdate(ContestProblemBase):
    pass

class ContestProblemInDBBase(ContestProblemBase):
    id: str
    contest_id: str
    
    class Config:
        from_attributes = True  # Cập nhật từ orm_mode

class ContestProblem(ContestProblemInDBBase):
    pass

class ContestProblemDetail(ContestProblem):
    problem: Optional[Problem] = None

# ContestParticipant schemas
class ContestParticipantBase(BaseModel):
    user_id: str
    score: Optional[int] = 0

class ContestParticipantCreate(ContestParticipantBase):
    pass

class ContestParticipantUpdate(ContestParticipantBase):
    pass

class ContestParticipantInDBBase(ContestParticipantBase):
    id: str
    contest_id: str
    joined_at: datetime
    
    class Config:
        from_attributes = True  # Cập nhật từ orm_mode

class ContestParticipant(ContestParticipantInDBBase):
    pass

# Contest schemas
class ContestBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_public: Optional[bool] = True
    
    @validator('end_time')
    def end_time_after_start_time(cls, v, values):
        if 'start_time' in values and v is not None:
            if values['start_time'] is not None and v <= values['start_time']:
                raise ValueError('End time must be after start time')
        return v

class ContestCreate(ContestBase):
    title: str
    description: str
    start_time: datetime
    end_time: datetime

class ContestUpdate(ContestBase):
    pass

class ContestInDBBase(ContestBase):
    id: str
    created_by: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True  # Cập nhật từ orm_mode

class Contest(ContestInDBBase):
    pass

class ContestDetail(Contest):
    participants: Optional[List[ContestParticipant]] = []
    problems: Optional[List[ContestProblemDetail]] = []
    participants_count: Optional[int] = 0


# Thêm class RegistrationStatusResponse vào cuối file
class RegistrationStatusResponse(BaseModel):
    status: str  # none, pending, approved, rejected

class ContestProblem(BaseModel):
    id: str
    contest_id: str
    problem_id: str
    order: int
    points: int = 100
    
    class Config:
        from_attributes = True  # Tương đương với orm_mode = True trong Pydantic v1