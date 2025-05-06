from typing import Any, Dict, Optional, Union, List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

from app.core.security import get_password_hash, verify_password
from app.models.users import User
from app.models.submissions import Submission  # Import model Submission
from app.schemas.users import UserCreate, UserUpdate

def get_by_id(db: Session, id: str) -> Optional[User]:
    return db.query(User).filter(User.id == id).first()

def get_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()

def get_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def get_multi(
    db: Session, *, skip: int = 0, limit: int = 100
) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()

def create(db: Session, *, obj_in: UserCreate) -> User:
    db_obj = User(
        username=obj_in.username,
        email=obj_in.email,
        hashed_password=get_password_hash(obj_in.password),
        full_name=obj_in.full_name,
        bio=obj_in.bio,
        is_active=obj_in.is_active,
        is_admin=obj_in.is_admin
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(
    db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]
) -> User:
    obj_data = jsonable_encoder(db_obj)
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    
    # Handle password separately
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        update_data["hashed_password"] = hashed_password
    
    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def delete(db: Session, *, id: str) -> User:
    # Xóa tất cả submissions của user trước
    db.query(Submission).filter(Submission.user_id == id).delete()
    
    # Sau đó xóa user
    obj = db.query(User).get(id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {id} not found"
        )
    db.delete(obj)
    db.commit()
    return obj

def authenticate(db: Session, *, username: str, password: str) -> Optional[User]:
    user = get_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user