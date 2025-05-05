from typing import Any, Dict, Optional, Union, List
from datetime import datetime
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder

from app import models  # Thêm dòng này để import models
from app.models.contests import Contest, ContestProblem, ContestParticipant, RegistrationRequest  # Thêm RegistrationRequest vào đây
from app.schemas.contests import ContestCreate, ContestUpdate

def get_by_id(db: Session, id: str) -> Optional[Contest]:
    return db.query(Contest).filter(Contest.id == id).first()

def get_by_id_with_details(db: Session, id: str) -> Optional[Contest]:
    return db.query(Contest).options(
        joinedload(Contest.problems).joinedload(ContestProblem.problem)
    ).filter(Contest.id == id).first()

def get_multi(
    db: Session, *, 
    skip: int = 0, 
    limit: int = 100,
    user_id: Optional[str] = None,
    is_public: Optional[bool] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
) -> List[Contest]:
    query = db.query(Contest)
    
    # Filter by creator
    if user_id:
        query = query.filter(Contest.created_by == user_id)
    
    # Filter by public/private
    if is_public is not None:
        query = query.filter(Contest.is_public == is_public)
    
    # Filter by status (upcoming, ongoing, finished)
    now = datetime.utcnow()
    if status == "upcoming":
        query = query.filter(Contest.start_time > now)
    elif status == "ongoing":
        query = query.filter(and_(Contest.start_time <= now, Contest.end_time >= now))
    elif status == "finished":
        query = query.filter(Contest.end_time < now)
    
    # Search by title or description
    if search:
        query = query.filter(
            or_(
                Contest.title.contains(search),
                Contest.description.contains(search)
            )
        )
    
    # Order by start time (most recent first)
    query = query.order_by(Contest.start_time.desc())
    
    return query.offset(skip).limit(limit).all()

def create(db: Session, *, obj_in: ContestCreate, created_by: str) -> Contest:
    obj_in_data = obj_in.model_dump()
    db_obj = Contest(**obj_in_data, created_by=created_by)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(
    db: Session, *, db_obj: Contest, obj_in: Union[ContestUpdate, Dict[str, Any]]
) -> Contest:
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

def delete(db: Session, *, id: str) -> Contest:
    obj = db.query(Contest).get(id)
    db.delete(obj)
    db.commit()
    return obj

# ContestProblem CRUD

def add_problem_to_contest(
    db: Session, *, contest_id: str, problem_id: str, order: int, points: int = 100
) -> ContestProblem:
    db_obj = ContestProblem(
        contest_id=contest_id,
        problem_id=problem_id,
        order=order,
        points=points
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def remove_problem_from_contest(db: Session, *, contest_id: str, problem_id: str) -> None:
    db.query(ContestProblem).filter(
        ContestProblem.contest_id == contest_id,
        ContestProblem.problem_id == problem_id
    ).delete()
    db.commit()

# ContestParticipant CRUD

def register_participant(db: Session, *, contest_id: str, user_id: str) -> ContestParticipant:
    # Check if already registered
    existing = db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest_id,
        ContestParticipant.user_id == user_id
    ).first()
    
    if existing:
        return existing
    
    db_obj = ContestParticipant(
        contest_id=contest_id,
        user_id=user_id,
        score=0
    )
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_participants(db: Session, *, contest_id: str) -> List[ContestParticipant]:
    return db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest_id
    ).all()

def update_score(db: Session, *, contest_id: str, user_id: str, score: int) -> ContestParticipant:
    participant = db.query(ContestParticipant).filter(
        ContestParticipant.contest_id == contest_id,
        ContestParticipant.user_id == user_id
    ).first()
    
    if participant:
        participant.score = score
        db.add(participant)
        db.commit()
        db.refresh(participant)
    
    return participant

def get_registration_request(db: Session, contest_id: str, user_id: str):
    """
    Lấy thông tin yêu cầu đăng ký của người dùng cho cuộc thi.
    """
    return db.query(RegistrationRequest).filter(  # Sử dụng RegistrationRequest trực tiếp
        RegistrationRequest.contest_id == contest_id,
        RegistrationRequest.user_id == user_id
    ).first()

def get_participant(db: Session, contest_id: str, user_id: str):
    """
    Kiểm tra xem người dùng đã là thành viên của cuộc thi chưa.
    """
    return db.query(ContestParticipant).filter(  # Sử dụng ContestParticipant trực tiếp
        ContestParticipant.contest_id == contest_id,
        ContestParticipant.user_id == user_id
    ).first()