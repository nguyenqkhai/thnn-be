from typing import Any, Dict, Optional, Union, List
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder

from app.models.submissions import Submission
from app.models.users import User
from app.models.problems import Problem
from app.schemas.submissions import SubmissionCreate, SubmissionUpdate

def get_by_id(db: Session, id: str) -> Optional[Submission]:
    """
    Lấy submission theo ID.
    """
    if not id or id == "undefined" or id == "null":
        return None
    return db.query(Submission).filter(Submission.id == id).first()

def get_by_id_with_details(db: Session, id: str) -> Optional[Submission]:
    """
    Lấy submission theo ID kèm thông tin chi tiết user và problem.
    """
    if not id or id == "undefined" or id == "null":
        return None
    return db.query(Submission).options(
        joinedload(Submission.user),
        joinedload(Submission.problem)
    ).filter(Submission.id == id).first()

def get_multi(
    db: Session, *, 
    skip: int = 0, 
    limit: int = 100,
    user_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    contest_id: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    view_mode: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> List[Submission]:
    """
    Lấy danh sách submissions với các tùy chọn lọc.
    """
    query = db.query(Submission).options(
        joinedload(Submission.user),
        joinedload(Submission.problem)
    )
    
    # Xử lý view_mode
    if view_mode == 'mine' and current_user_id:
        user_id = current_user_id
    
    # Lọc theo user
    if user_id:
        query = query.filter(Submission.user_id == user_id)
    
    # Lọc theo problem
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    
    # Lọc theo contest
    if contest_id:
        query = query.filter(Submission.contest_id == contest_id)
    
    # Lọc theo trạng thái
    if status:
        query = query.filter(Submission.status == status)
    
    # Lọc theo ngôn ngữ
    if language:
        query = query.filter(Submission.language == language)
    
    # Sắp xếp theo thời gian nộp (mới nhất trước)
    query = query.order_by(Submission.submitted_at.desc())
    
    return query.offset(skip).limit(limit).all()

def count(
    db: Session, *, 
    user_id: Optional[str] = None,
    problem_id: Optional[str] = None,
    contest_id: Optional[str] = None,
    status: Optional[str] = None,
    language: Optional[str] = None,
    view_mode: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> int:
    """
    Đếm số lượng submissions với các tùy chọn lọc.
    """
    query = db.query(Submission)
    
    # Xử lý view_mode
    if view_mode == 'mine' and current_user_id:
        user_id = current_user_id
    
    # Lọc theo user
    if user_id:
        query = query.filter(Submission.user_id == user_id)
    
    # Lọc theo problem
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    
    # Lọc theo contest
    if contest_id:
        query = query.filter(Submission.contest_id == contest_id)
    
    # Lọc theo trạng thái
    if status:
        query = query.filter(Submission.status == status)
    
    # Lọc theo ngôn ngữ
    if language:
        query = query.filter(Submission.language == language)
    
    return query.count()

def create(db: Session, *, obj_in: SubmissionCreate, user_id: str) -> Submission:
    """
    Tạo mới một submission.
    """
    obj_in_data = obj_in.model_dump()
    db_obj = Submission(**obj_in_data, user_id=user_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(
    db: Session, *, db_obj: Submission, obj_in: Union[SubmissionUpdate, Dict[str, Any]]
) -> Submission:
    """
    Cập nhật thông tin submission.
    """
    obj_data = jsonable_encoder(db_obj)
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)
    
    for field in obj_data:
        if field in update_data:
            setattr(db_obj, field, update_data[field])
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def remove(db: Session, *, id: str) -> Submission:
    """
    Xóa một submission.
    """
    submission = db.query(Submission).get(id)
    if submission:
        db.delete(submission)
        db.commit()
    return submission

def get_latest_submission(
    db: Session, *, user_id: str, problem_id: str, contest_id: Optional[str] = None
) -> Optional[Submission]:
    """
    Lấy bài nộp mới nhất của một người dùng cho một bài toán.
    """
    query = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.problem_id == problem_id
    )
    
    if contest_id:
        query = query.filter(Submission.contest_id == contest_id)
    
    return query.order_by(Submission.submitted_at.desc()).first()

def get_accepted_submissions_by_problem(
    db: Session, *, user_id: str, problem_ids: List[str]
) -> Dict[str, Submission]:
    """
    Lấy các bài nộp đã được chấp nhận của một người dùng cho nhiều bài toán.
    """
    accepted_submissions = {}
    
    submissions = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.problem_id.in_(problem_ids),
        Submission.status == "accepted"
    ).order_by(Submission.submitted_at.asc()).all()
    
    # Chỉ lấy submission đầu tiên được chấp nhận cho mỗi problem
    for submission in submissions:
        if submission.problem_id not in accepted_submissions:
            accepted_submissions[submission.problem_id] = submission
    
    return accepted_submissions

def count_accepted_submissions(db: Session, *, user_id: str) -> int:
    """
    Đếm số lượng bài nộp đã được chấp nhận của một người dùng.
    """
    return db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.status == "accepted"
    ).count()

def get_user_statistics(db: Session, *, user_id: str) -> Dict[str, Any]:
    """
    Lấy thống kê bài nộp của một người dùng.
    """
    total = db.query(Submission).filter(Submission.user_id == user_id).count()
    
    by_status = {}
    statuses = ["accepted", "wrong_answer", "time_limit_exceeded", 
                "memory_limit_exceeded", "runtime_error", "compilation_error", "pending"]
    
    for status in statuses:
        count = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.status == status
        ).count()
        by_status[status] = count
    
    by_language = {}
    languages = db.query(Submission.language).filter(
        Submission.user_id == user_id
    ).distinct().all()
    
    for (language,) in languages:
        count = db.query(Submission).filter(
            Submission.user_id == user_id,
            Submission.language == language
        ).count()
        by_language[language] = count
    
    # Tính số lượng bài toán đã giải
    problems_solved = db.query(Submission.problem_id).filter(
        Submission.user_id == user_id,
        Submission.status == "accepted"
    ).distinct().count()
    
    # Thêm thông tin về thời gian trung bình và bộ nhớ trung bình
    execution_time_avg = db.query(func.avg(Submission.execution_time_ms)).filter(
        Submission.user_id == user_id,
        Submission.status == "accepted"
    ).scalar() or 0
    
    memory_used_avg = db.query(func.avg(Submission.memory_used_kb)).filter(
        Submission.user_id == user_id,
        Submission.status == "accepted"
    ).scalar() or 0
    
    # Tìm bài nộp mới nhất
    latest_submission = db.query(Submission).filter(
        Submission.user_id == user_id
    ).order_by(Submission.submitted_at.desc()).first()
    
    latest_submission_info = None
    if latest_submission:
        latest_submission_info = {
            "id": latest_submission.id,
            "problem_id": latest_submission.problem_id,
            "status": latest_submission.status,
            "submitted_at": latest_submission.submitted_at.isoformat()
        }
    
    return {
        "total": total,
        "problems_solved": problems_solved,
        "by_status": by_status,
        "by_language": by_language,
        "execution_time_avg": round(execution_time_avg, 2),
        "memory_used_avg": round(memory_used_avg, 2),
        "latest_submission": latest_submission_info
    }