from typing import Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.schemas.contests import ContestProblemDetail, RegistrationStatusResponse

# Phiên bản sửa đổi của endpoint PUT /contests/{contest_id}/problems/{problem_id}
# Có hai cách tiếp cận để sửa lỗi 404 Not Found:

# Cách 1: Nếu problem_id trong URL là id của bản ghi ContestProblem
@router.put("/{contest_id}/problems/{problem_id}", response_model=schemas.ContestProblem)
def update_problem_in_contest_by_id(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    problem_id: str = Path(...),  # Đây là id của bản ghi ContestProblem
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

# Cách 2: Nếu problem_id trong URL là problem_id của bài toán
@router.put("/{contest_id}/problems/{problem_id}/update", response_model=schemas.ContestProblem)
def update_problem_in_contest(
    *,
    db: Session = Depends(deps.get_db),
    contest_id: str = Path(...),
    problem_id: str = Path(...),  # Đây là problem_id của bài toán
    order: int = Body(None),
    points: int = Body(None),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Cập nhật thông tin bài toán trong cuộc thi theo problem_id của bài toán.
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
    
    # Tìm bài toán trong cuộc thi theo problem_id của bài toán
    contest_problem = db.query(models.ContestProblem).filter(
        models.ContestProblem.contest_id == contest_id,
        models.ContestProblem.problem_id == problem_id
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