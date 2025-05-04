from typing import Any, List, Optional
from datetime import datetime
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services import judge
from app.models.languages import Language

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/test", response_model=schemas.SubmissionTestResult)
async def test_submission(
    test_data: schemas.SubmissionTestInput,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Test code với input tùy chỉnh.
    """
    try:
        # Kiểm tra dữ liệu đầu vào
        if not test_data.code or not test_data.problem_id or not test_data.language or not test_data.input:
            raise HTTPException(
                status_code=400, 
                detail="Thiếu thông tin bắt buộc"
            )
        
        # Lấy thông tin ngôn ngữ
        language = db.query(Language).filter(
            Language.identifier == test_data.language,
            Language.is_active == True
        ).first()
        
        if not language:
            raise HTTPException(
                status_code=400, 
                detail="Ngôn ngữ lập trình không được hỗ trợ"
            )
        
        # Lấy thông tin bài toán để kiểm tra quyền truy cập
        problem = db.query(models.Problem).filter(
            models.Problem.id == test_data.problem_id
        ).first()
        
        if not problem:
            raise HTTPException(
                status_code=404, 
                detail="Không tìm thấy bài toán này"
            )
        
        # Kiểm tra nếu problem là private và user không phải admin hoặc người tạo
        if not problem.is_public and not current_user.is_admin and problem.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền truy cập bài toán này"
            )
        
        # Gọi service để test code
        test_result = await judge.test_code(
            user_id=current_user.id,
            problem_id=test_data.problem_id,
            code=test_data.code,
            language_id=language.id,
            input=test_data.input,
            db=db
        )
        
        return test_result
        
    except Exception as e:
        logger.error(f"Error testing submission: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Có lỗi xảy ra khi test code: {str(e)}"
        )

@router.get("/", response_model=List[schemas.SubmissionWithDetails])
def read_submissions(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    problem_id: Optional[str] = None,
    contest_id: Optional[str] = None,
    status: Optional[str] = Query(None, enum=[
        "pending", "accepted", "wrong_answer", "time_limit_exceeded",
        "memory_limit_exceeded", "runtime_error", "compilation_error"
    ]),
    language: Optional[str] = Query(None, enum=["c", "cpp", "python", "pascal"]),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve submissions.
    """
    # Normal users can only see their own submissions
    if not current_user.is_admin:
        submissions = crud.submissions.get_multi(
            db, skip=skip, limit=limit, user_id=current_user.id, 
            problem_id=problem_id, contest_id=contest_id,
            status=status, language=language
        )
    else:
        # Admins can see all submissions
        submissions = crud.submissions.get_multi(
            db, skip=skip, limit=limit, problem_id=problem_id, 
            contest_id=contest_id, status=status, language=language
        )
    
    # Enhance submissions with additional details
    result = []
    for sub in submissions:
        details = schemas.SubmissionWithDetails(
            **{key: getattr(sub, key) for key in schemas.Submission.__annotations__.keys()},
            problem_title=sub.problem.title if sub.problem else None,
            username=sub.user.username if sub.user else None
        )
        result.append(details)
    
    return result

@router.post("/", response_model=schemas.Submission)
def create_submission(
    *,
    db: Session = Depends(deps.get_db),
    submission_in: schemas.SubmissionCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create new submission.
    """
    # Check if problem exists
    problem = db.query(models.Problem).filter(models.Problem.id == submission_in.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found",
        )
    
    # Kiểm tra nếu problem là private và user không phải admin hoặc người tạo
    if not problem.is_public and not current_user.is_admin and problem.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Bạn không có quyền truy cập bài toán này"
        )
    
    # If submission is for a contest, validate
    if submission_in.contest_id:
        contest = crud.contests.get_by_id(db, id=submission_in.contest_id)
        if not contest:
            raise HTTPException(
                status_code=404,
                detail="Contest not found",
            )
        
        # Check if user is registered for the contest
        participants = crud.contests.get_participants(db, contest_id=submission_in.contest_id)
        is_participant = any(p.user_id == current_user.id for p in participants)
        if not is_participant:
            raise HTTPException(
                status_code=403,
                detail="You are not registered for this contest",
            )
        
        # Check if contest is active
        now = datetime.utcnow()
        if now < contest.start_time or now > contest.end_time:
            raise HTTPException(
                status_code=400,
                detail="Contest is not active",
            )
        
        # Check if problem is part of the contest
        contest_problems = [cp.problem_id for cp in contest.problems]
        if submission_in.problem_id not in contest_problems:
            raise HTTPException(
                status_code=400,
                detail="This problem is not part of the contest",
            )
    
    # Create submission
    submission = crud.submissions.create(db, obj_in=submission_in, user_id=current_user.id)
    
    # In a real system, we would send this submission to a judging queue
    # For now, we'll simulate judging synchronously
    try:
        # Judge the submission
        judge_result = judge.judge_submission(db, submission)
        
        # Update submission with judge result
        update_data = schemas.SubmissionUpdate(
            status=judge_result["status"],
            execution_time_ms=judge_result["execution_time_ms"],
            memory_used_kb=judge_result["memory_used_kb"]
        )
        submission = crud.submissions.update(db, db_obj=submission, obj_in=update_data)
        
        # Thêm thông tin về kết quả test vào thuộc tính details
        if hasattr(submission, 'details'):
            submission.details = judge_result.get("details", None)
        
        # If this is a contest submission and it's accepted, update user's score
        if submission.contest_id and submission.status == "accepted":
            # Find contest problem points
            contest_problem = next(
                (cp for cp in contest.problems if cp.problem_id == submission.problem_id), 
                None
            )
            if contest_problem:
                # Update participant's score
                crud.contests.update_score(
                    db, 
                    contest_id=submission.contest_id, 
                    user_id=current_user.id,
                    score=contest_problem.points
                )
    except Exception as e:
        logger.error(f"Error judging submission: {str(e)}")
        # In case of error in judging, mark as runtime error
        update_data = schemas.SubmissionUpdate(
            status="runtime_error",
            execution_time_ms=0,
            memory_used_kb=0
        )
        submission = crud.submissions.update(db, db_obj=submission, obj_in=update_data)
        
        # Thêm thông tin lỗi
        if hasattr(submission, 'details'):
            submission.details = {
                "total_test_cases": 0,
                "passed_test_cases": 0,
                "failed_test_cases": 0,
                "test_results": [],
                "error": str(e)
            }
    
    return submission

@router.get("/{submission_id}", response_model=schemas.Submission)
def read_submission(
    *,
    db: Session = Depends(deps.get_db),
    submission_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get submission by ID.
    """
    submission = crud.submissions.get_by_id(db, id=submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Submission not found",
        )
    
    # Check if user has access to submission
    if not current_user.is_admin and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have access to this submission",
        )
    
    return submission

@router.delete("/{submission_id}", response_model=schemas.Message)
def delete_submission(
    *,
    db: Session = Depends(deps.get_db),
    submission_id: str = Path(...),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a submission.
    """
    submission = crud.submissions.get_by_id(db, id=submission_id)
    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Submission not found",
        )
    
    # Only admin or the submission's owner can delete it
    if not current_user.is_admin and submission.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this submission",
        )
    
    # Delete the submission
    crud.submissions.remove(db, id=submission_id)
    
    return {"message": "Submission deleted successfully"}