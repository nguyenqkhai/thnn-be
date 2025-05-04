from typing import Any, List

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[schemas.User])
def read_users(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_admin),
) -> Any:
    """
    Retrieve users. Admin only.
    """
    users = crud.users.get_multi(db, skip=skip, limit=limit)
    return users

@router.get("/me", response_model=schemas.User)
def read_user_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user

@router.put("/me", response_model=schemas.User)
def update_user_me(
    *,
    db: Session = Depends(deps.get_db),
    full_name: str = Body(None),
    email: str = Body(None),
    password: str = Body(None),
    bio: str = Body(None),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update own user.
    """
    current_user_data = schemas.UserUpdate(
        full_name=full_name or current_user.full_name,
        email=email or current_user.email,
        password=password,
        bio=bio or current_user.bio
    )
    user = crud.users.update(db, db_obj=current_user, obj_in=current_user_data)
    return user

@router.get("/{user_id}", response_model=schemas.User)
def read_user_by_id(
    user_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
    db: Session = Depends(deps.get_db),
) -> Any:
    """
    Get a specific user by id.
    """
    user = crud.users.get_by_id(db, id=user_id)
    if user == current_user:
        return user
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can access other users data",
        )
    return user