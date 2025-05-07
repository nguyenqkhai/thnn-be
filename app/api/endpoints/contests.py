from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.schemas.contests import ContestProblemDetail, RegistrationStatusResponse

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
    if not current_user.is_admin:
        contests = crud.contests.get_multi(
            db, skip=skip, limit=limit, is_public=True, status=status, search=search
        )
    else:
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
    
    # Tạo danh sách ContestProblemDetail từ contest.problems
    problem_details = []
    for prob in contest.problems:
        # Lấy thông tin chi tiết về problem
        problem_detail = crud.problems.get_by_id(db, id=prob.problem_id)
        problem_details.append(schemas.ContestProblemDetail(
            id=prob.id,
            contest_id=prob.contest_id,
            problem_id=prob.problem_id,
            order=prob.order,
            points=prob.points,
            problem=problem_detail
        ))
    
    # Tạo response với đầy đủ các trường yêu cầu
    response = schemas.ContestDetail(
        id=contest.id,
        title=contest.title,
        description=contest.description,
        start_time=contest.start_time,
        end_time=contest.end_time,
        is_public=contest.is_public,
        created_by=contest.created_by,
        created_at=contest.created_at,
        problems=problem_details,
        participants=participants,
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

@router.put("/{contest_id}/problems/{problem_id}", response_model=schemas.ContestProblem)
def update_problem_in_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    problem_id: str = Path(...),
    order: int = Body(None),
    points: int = Body(None),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Cập nhật thông tin bài toán trong cuộc thi theo ID của bản ghi ContestProblem.
    """
    # Kiểm tra cuộc thi tồn tại
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc thi",
        )
    
    # Kiểm tra quyền cập nhật
    if not current_user.is_admin and contest.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền cập nhật bài toán trong cuộc thi này",
        )
    
    # Kiểm tra cuộc thi đã bắt đầu chưa
    now = datetime.utcnow()
    if now >= contest.start_time:
        raise HTTPException(
            status_code=400,
            detail="Không thể cập nhật cuộc thi đã bắt đầu",
        )
    
    # Tìm bài toán trong cuộc thi theo ID của bản ghi ContestProblem
    contest_problem = db.query(models.ContestProblem).filter(
        models.ContestProblem.id == problem_id,
        models.ContestProblem.contest_id == contest_id
    ).first()
    
    if not contest_problem:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bài toán trong cuộc thi này",
        )
    
    # Cập nhật thông tin
    if order is not None:
        contest_problem.order = order
    if points is not None:
        contest_problem.points = points
    
    db.add(contest_problem)
    db.commit()
    db.refresh(contest_problem)
    
    return contest_problem

@router.delete("/{contest_id}/problems/{problem_id}", response_model=schemas.ContestProblem)
def delete_problem_from_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    problem_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Xóa bài toán khỏi cuộc thi.
    """
    # Kiểm tra cuộc thi tồn tại
    contest = crud.contests.get_by_id(db, id=contest_id)
    if not contest:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy cuộc thi",
        )
    
    # Kiểm tra quyền cập nhật
    if not current_user.is_admin and contest.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền xóa bài toán khỏi cuộc thi này",
        )
    
    # Kiểm tra cuộc thi đã bắt đầu chưa
    now = datetime.utcnow()
    if now >= contest.start_time:
        raise HTTPException(
            status_code=400,
            detail="Không thể cập nhật cuộc thi đã bắt đầu",
        )
    
    # Tìm bài toán trong cuộc thi
    # Đầu tiên, thử tìm theo problem_id (trường hợp problem_id là problem_id của bài toán)
    contest_problem = db.query(models.ContestProblem).filter(
        models.ContestProblem.contest_id == contest_id,
        models.ContestProblem.problem_id == problem_id
    ).first()
    
    # Nếu không tìm thấy, thử tìm theo id (trường hợp problem_id là id của bản ghi ContestProblem)
    if not contest_problem:
        contest_problem = db.query(models.ContestProblem).filter(
            models.ContestProblem.contest_id == contest_id,
            models.ContestProblem.id == problem_id
        ).first()
    
    if not contest_problem:
        raise HTTPException(
            status_code=404,
            detail="Không tìm thấy bài toán trong cuộc thi này",
        )
    
    # Lưu thông tin bài toán trước khi xóa để trả về
    result = schemas.ContestProblem.from_orm(contest_problem)
    
    # Xóa bài toán khỏi cuộc thi
    db.delete(contest_problem)
    db.commit()
    
    return result