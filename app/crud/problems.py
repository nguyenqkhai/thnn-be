from typing import Any, Dict, Optional, Union, List
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder

from app.models.problems import Problem, TestCase
from app.schemas.problems import ProblemCreate, ProblemUpdate, TestCaseCreate

def get_by_id(db: Session, id: str) -> Optional[Problem]:
    return db.query(Problem).filter(Problem.id == id).first()

def get_by_id_with_test_cases(db: Session, id: str) -> Optional[Problem]:
    return db.query(Problem).options(joinedload(Problem.test_cases)).filter(Problem.id == id).first()

def get_multi(
    db: Session, *, 
    skip: int = 0, 
    limit: int = 100,
    user_id: Optional[str] = None,
    is_public: Optional[bool] = None,
    difficulty: Optional[str] = None,
    search: Optional[str] = None
) -> List[Problem]:
    query = db.query(Problem)
    
    # Filter by owner
    if user_id:
        query = query.filter(Problem.created_by == user_id)
    
    # Filter by public/private
    if is_public is not None:
        query = query.filter(Problem.is_public == is_public)
    
    # Filter by difficulty
    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)
    
    # Search by title or description
    if search:
        query = query.filter(
            or_(
                Problem.title.contains(search),
                Problem.description.contains(search)
            )
        )
    
    return query.offset(skip).limit(limit).all()

def create(db: Session, *, obj_in: ProblemCreate, created_by: str) -> Problem:
    obj_in_data = obj_in.model_dump()
    db_obj = Problem(**obj_in_data, created_by=created_by)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def update(
    db: Session, *, db_obj: Problem, obj_in: Union[ProblemUpdate, Dict[str, Any]]
) -> Problem:
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

def delete(db: Session, *, id: str) -> Problem:
    obj = db.query(Problem).get(id)
    db.delete(obj)
    db.commit()
    return obj

# Test Cases CRUD

def create_test_case(db: Session, *, obj_in: TestCaseCreate, problem_id: str) -> TestCase:
    obj_in_data = obj_in.model_dump()
    db_obj = TestCase(**obj_in_data, problem_id=problem_id)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_test_cases(db: Session, *, problem_id: str) -> List[TestCase]:
    return db.query(TestCase).filter(TestCase.problem_id == problem_id).order_by(TestCase.order).all()

def delete_test_case(db: Session, *, id: str) -> TestCase:
    obj = db.query(TestCase).get(id)
    db.delete(obj)
    db.commit()
    return obj