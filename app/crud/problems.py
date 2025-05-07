from typing import Any, Dict, Optional, Union, List
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from fastapi.encoders import jsonable_encoder

from app.models.problems import Problem, TestCase
from app.models.submissions import Submission
from app.models.contests import ContestProblem
from app.schemas.problems import ProblemCreate, ProblemUpdate, TestCaseCreate, TestCaseUpdate
import uuid

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
    try:
        # First, find the problem to delete
        problem = db.query(Problem).filter(Problem.id == id).first()
        if not problem:
            return None
        
        # Delete related submissions
        db.query(Submission).filter(Submission.problem_id == id).delete(synchronize_session=False)
        
        # Delete test cases (even though we have ON DELETE CASCADE)
        db.query(TestCase).filter(TestCase.problem_id == id).delete(synchronize_session=False)
        
        # Delete contest problem links
        db.query(ContestProblem).filter(ContestProblem.problem_id == id).delete(synchronize_session=False)
        
        # Finally delete the problem
        db.delete(problem)
        db.commit()
        
        return problem
    except Exception as e:
        db.rollback()
        print(f"Error deleting problem: {str(e)}")
        raise

# Test Cases CRUD

def create_test_case(db: Session, *, obj_in: TestCaseCreate, problem_id: str) -> TestCase:
    """
    Create a new test case for a problem
    """
    obj_in_data = obj_in.model_dump()
    # Create a new ID for the test case if not present
    test_case_id = str(uuid.uuid4())
    
    db_obj = TestCase(
        id=test_case_id,
        problem_id=problem_id,
        **obj_in_data
    )
    
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_test_case_by_id(db: Session, *, test_case_id: str) -> Optional[TestCase]:
    """
    Get test case by ID
    """
    return db.query(TestCase).filter(TestCase.id == test_case_id).first()

def get_test_case(db: Session, *, problem_id: str, test_case_id: str) -> Optional[TestCase]:
    """
    Get test case by problem ID and test case ID
    """
    return db.query(TestCase).filter(
        TestCase.problem_id == problem_id,
        TestCase.id == test_case_id
    ).first()

def get_test_cases(db: Session, *, problem_id: str) -> List[TestCase]:
    """
    Get all test cases for a problem
    """
    return db.query(TestCase).filter(TestCase.problem_id == problem_id).order_by(TestCase.order).all()

def update_test_case(db: Session, *, test_case_id: str, obj_in: Union[Dict[str, Any], TestCaseUpdate]) -> Optional[TestCase]:
    """
    Update a test case
    """
    test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
    if not test_case:
        return None
    
    # Convert obj_in to dict if needed
    if hasattr(obj_in, 'model_dump'):
        update_data = obj_in.model_dump(exclude_unset=True)
    else:
        update_data = obj_in
    
    # Update fields
    for field, value in update_data.items():
        if hasattr(test_case, field):
            setattr(test_case, field, value)
    
    db.add(test_case)
    db.commit()
    db.refresh(test_case)
    return test_case

def delete_test_case(db: Session, *, id: str) -> Optional[TestCase]:
    """
    Delete a test case by ID
    """
    test_case = db.query(TestCase).get(id)
    if not test_case:
        return None
    
    db.delete(test_case)
    db.commit()
    return test_case

def delete_test_cases(db: Session, *, problem_id: str) -> int:
    """
    Delete all test cases for a problem
    """
    count = db.query(TestCase).filter(TestCase.problem_id == problem_id).delete(synchronize_session=False)
    db.commit()
    return count