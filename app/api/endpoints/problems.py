from typing import Any, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps
from app.schemas.problems import TestCaseUpdate, TestCaseCreate, ProblemCreate, ProblemUpdate

router = APIRouter()

@router.get("/", response_model=List[schemas.problems.Problem])
def read_problems(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    difficulty: Optional[str] = Query(None, enum=["easy", "medium", "hard"]),
    search: Optional[str] = None,
    current_user: Optional[models.User] = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve problems.
    """
    # Normal users can only see public problems
    if not current_user.is_admin:
        problems = crud.problems.get_multi(
            db, skip=skip, limit=limit, is_public=True, difficulty=difficulty, search=search
        )
    else:
        # Admins can see all problems
        problems = crud.problems.get_multi(
            db, skip=skip, limit=limit, difficulty=difficulty, search=search
        )
    
    return problems

@router.post("/", response_model=schemas.problems.Problem)
def create_problem(
    *,
    db: Session = Depends(deps.get_db),
    problem_in: ProblemCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new problem.
    Only admin can create problems.
    """
    # Only admin can create problems
    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can create problems",
        )
    
    # Create a new problem
    problem = crud.problems.create(db, obj_in=problem_in, created_by=current_user.id)
    
    # Automatically create a sample test case from example input/output
    if problem and problem_in.example_input and problem_in.example_output:
        try:
            # Create sample test case
            sample_test_case = TestCaseCreate(
                input=problem_in.example_input,
                expected_output=problem_in.example_output,
                is_sample=True,
                order=1
            )
            
            # Add test case to the problem
            crud.problems.create_test_case(db, obj_in=sample_test_case, problem_id=problem.id)
        except Exception as e:
            # Log error but don't affect problem creation
            print(f"Error creating sample test case: {str(e)}")
            # Could add more detailed logging here
    
    return problem

@router.get("/{problem_id}", response_model=schemas.problems.ProblemWithTestCases)
def read_problem(
    *,
    db: Session = Depends(deps.get_db),
    problem_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get problem by ID.
    """
    problem = crud.problems.get_by_id_with_test_cases(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Check if user has access to problem
    if not problem.is_public and not current_user.is_admin and problem.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this problem",
        )
    
    return problem

@router.put("/{problem_id}", response_model=schemas.problems.Problem)
def update_problem(
    *,
    db: Session = Depends(deps.get_db),
    problem_id: str = Path(...),
    problem_in: ProblemUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a problem.
    """
    problem = crud.problems.get_by_id(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Check if user has permission to update the problem
    if not current_user.is_admin and problem.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this problem",
        )
    
    problem = crud.problems.update(db, db_obj=problem, obj_in=problem_in)
    return problem

@router.delete("/{problem_id}", response_model=schemas.problems.Problem)
def delete_problem(
    *,
    db: Session = Depends(deps.get_db),
    problem_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a problem.
    """
    problem = crud.problems.get_by_id(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Check if user has permission to delete the problem
    if not current_user.is_admin and problem.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this problem",
        )
    
    problem = crud.problems.delete(db, id=problem_id)
    return problem

@router.post("/{problem_id}/test-cases", response_model=schemas.problems.TestCase)
def create_test_case(
    *,
    db: Session = Depends(deps.get_db),
    problem_id: str = Path(...),
    test_case_in: TestCaseCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a test case for a problem.
    """
    problem = crud.problems.get_by_id(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Check if user has permission to add test cases
    if not current_user.is_admin and problem.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to add test cases to this problem",
        )
    
    test_case = crud.problems.create_test_case(db, obj_in=test_case_in, problem_id=problem_id)
    return test_case

@router.put("/{problem_id}/test-cases/{test_case_id}", response_model=schemas.problems.TestCase)
def update_test_case(
    *,
    db: Session = Depends(deps.get_db),
    problem_id: str = Path(...),
    test_case_id: str = Path(...),
    test_case_in: TestCaseUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a test case for a problem.
    """
    # Check if problem exists
    problem = crud.problems.get_by_id(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Check access rights
    if not current_user.is_admin and problem.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update test cases for this problem",
        )
    
    # Check if test case belongs to this problem
    test_case = crud.problems.get_test_case(db, problem_id=problem_id, test_case_id=test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=404,
            detail="Test case not found for this problem",
        )
    
    # Update test case
    updated_test_case = crud.problems.update_test_case(db, test_case_id=test_case_id, obj_in=test_case_in)
    return updated_test_case

@router.get("/{problem_id}/test-cases", response_model=List[schemas.problems.TestCase])
def read_test_cases(
    *,
    db: Session = Depends(deps.get_db),
    problem_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get test cases for a problem.
    """
    problem = crud.problems.get_by_id(db, id=problem_id)
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Check if user has access to problem's test cases
    if not current_user.is_admin and problem.created_by != current_user.id:
        # For non-admins, only return sample test cases
        test_cases = crud.problems.get_test_cases(db, problem_id=problem_id)
        return [tc for tc in test_cases if tc.is_sample]
    
    # Admins and problem creators can see all test cases
    test_cases = crud.problems.get_test_cases(db, problem_id=problem_id)
    return test_cases