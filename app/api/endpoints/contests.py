from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[schemas.Contest])
def read_contests(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, enum=["upcoming", "ongoing", "finished"]),
    search: Optional[str] = None,
    current_user: Optional[models.User] = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve contests.
    """
    # Normal users can only see public contests
    if not current_user.is_admin:
        contests = crud.contests.get_multi(
            db, skip=skip, limit=limit, is_public=True, status=status, search=search
        )
    else:
        # Admins can see all contests
        contests = crud.contests.get_multi(
            db, skip=skip, limit=limit, status=status, search=search
        )
    
    return contests

@router.post("/", response_model=schemas.Contest)
def create_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_in: schemas.ContestCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new contest.
    """
    # Only admin can create contests
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can create contests",
        )
    
    contest = crud.contests.create(db, obj_in=contest_in, created_by=current_user.id)
    return contest

@router.get("/{contest_id}", response_model=schemas.ContestDetail)
def read_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get contest by ID.
    """
    contest = crud.contests.get_by_id_with_details(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Contest not found",
        )
    
    # Check if user has access to contest
    if not contest.is_public and not current_user.is_admin and contest.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this contest",
        )
    
    # Get participant count
    participants = crud.contests.get_participants(db, contest_id=contest_id)
    
    # Create response with participant count
    response = schemas.ContestDetail(
        **{key: getattr(contest, key) for key in schemas.Contest.__annotations__.keys()},
        problems=contest.problems,
        participants_count=len(participants)
    )
    
    return response

@router.put("/{contest_id}", response_model=schemas.Contest)
def update_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    contest_in: schemas.ContestUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a contest.
    """
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Contest not found",
        )
    
    # Check if user has permission to update the contest
    if not current_user.is_admin and contest.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this contest",
        )
    
    # Check if contest has already started
    now = datetime.utcnow()
    if now >= contest.start_time:
        raise HTTPException(
            status_code=400,
            detail="Cannot update a contest that has already started",
        )
    
    contest = crud.contests.update(db, db_obj=contest, obj_in=contest_in)
    return contest

@router.delete("/{contest_id}", response_model=schemas.Contest)
def delete_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a contest.
    """
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Contest not found",
        )
    
    # Check if user has permission to delete the contest
    if not current_user.is_admin and contest.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this contest",
        )
    
    contest = crud.contests.delete(db, id=contest_id)
    return contest

@router.post("/{contest_id}/problems", response_model=schemas.ContestProblem)
def add_problem_to_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    problem_id: str = Body(...),
    order: int = Body(...),
    points: int = Body(100),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Add a problem to a contest.
    """
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Contest not found",
        )
    
    # Check if user has permission to add problems to the contest
    if not current_user.is_admin and contest.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to add problems to this contest",
        )
    
    # Check if contest has already started
    now = datetime.utcnow()
    if now >= contest.start_time:
        raise HTTPException(
            status_code=400,
            detail="Cannot modify a contest that has already started",
        )
    
    # Check if problem exists
    problem = crud.problems.get_by_id(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    contest_problem = crud.contests.add_problem_to_contest(
        db, contest_id=contest_id, problem_id=problem_id, order=order, points=points
    )
    return contest_problem

@router.post("/{contest_id}/register", response_model=schemas.ContestParticipant)
def register_for_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Register current user for a contest.
    """
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Contest not found",
        )
    
    # Check if contest is public or user is admin
    if not contest.is_public and not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this contest",
        )
    
    # Check if contest has already ended
    now = datetime.utcnow()
    if now >= contest.end_time:
        raise HTTPException(
            status_code=400,
            detail="Cannot register for a contest that has already ended",
        )
    
    participant = crud.contests.register_participant(
        db, contest_id=contest_id, user_id=current_user.id
    )
    return participant

@router.get("/{contest_id}/participants", response_model=List[schemas.ContestParticipant])
def get_contest_participants(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get list of participants for a contest.
    """
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Contest not found",
        )
    
    participants = crud.contests.get_participants(db, contest_id=contest_id)
    return participants