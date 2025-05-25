from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
import re

# Shared properties
class UserBase(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    bio: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_]+$', v):
                raise ValueError('Username must be alphanumeric')
            if len(v) < 3 or len(v) > 50:
                raise ValueError('Username must be between 3 and 50 characters')
        return v

# Properties to receive on user creation
class UserCreate(UserBase):
    username: str
    email: EmailStr
    password: str
    
    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Properties to receive on user update
class UserUpdate(UserBase):
    password: Optional[str] = None
    
    @validator('password')
    def password_min_length(cls, v):
        if v is not None and len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v

# Properties shared by models returned from API
class UserInDBBase(UserBase):
    id: str
    rating: int
    created_at: datetime
    
    class Config:
        from_attributes = True  # Thay thế cho orm_mode trong pydantic v2

# Properties to return to client
class User(UserInDBBase):
    pass

# Properties stored in DB (includes hashed_password)
class UserInDB(UserInDBBase):
    hashed_password: str

# For authentication response
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None