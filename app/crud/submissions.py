from typing import Any, Dict, Optional, Union, List
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder

from app.models.submissions import Submission
from app.models.users import User
from app.models.problems import Problem
from app.schemas.submissions import SubmissionCreate, SubmissionUpdate

def get_by_id(db: Session, id: str) -> Optional[Submission]:
    return db.query(Submission).filter(Submission.id == id).first()

def get_by_id_with_details(db: Session, id: str) -> Optional[Submission]:
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
    language: Optional[str] = None
) -> List[Submission]:
    query = db.query(Submission).options(
        joinedload(Submission.user),
        joinedload(Submission.problem)
    )
    
    # Filter by owner
    if user_id:
        query = query.filter(Submission.user_id == user_id)
    
    # Filter by problem
    if problem_id:
        query = query.filter(Submission.problem_id == problem_id)
    
    # Filter by contest
    if contest_id:
        query = query.filter(Submission.contest_id == contest_id)
    
    # Filter by status
    if status:
        query = query.filter(Submission.status == status)
    
    # Filter by language
    if language:
        query = query.filter(Submission.language == language)
    
    # Order by submission time (most recent first)
    query = query.order_by(Submission.submitted_at.desc())
    
    return query.offset(skip).limit(limit).all()

def create(db: Session, *, obj_in: SubmissionCreate, user_id: str) -> Submission:
    obj_in_data = obj_in.model_dump()
    db_obj = Submission(**obj_in_data, user_id=user_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(
    db: Session, *, db_obj: Submission, obj_in: Union[SubmissionUpdate, Dict[str, Any]]
) -> Submission:
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

def get_latest_submission(
    db: Session, *, user_id: str, problem_id: str, contest_id: Optional[str] = None
) -> Optional[Submission]:
    query = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.problem_id == problem_id
    )
    
    if contest_id:
        query = query.filter(Submission.contest_id == contest_id)
    
    return query.order_by(Submission.submitted_at.desc()).first()

def count_accepted_submissions(db: Session, *, user_id: str) -> int:
    return db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.status == "accepted"
    ).count()