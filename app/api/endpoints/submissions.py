from typing import Any, List, Optional, Dict
from datetime import datetime
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Response
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
        if not test_data.code or not test_data.problem_id or not test_data.language:
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
        
        # Đảm bảo kết quả trả về luôn có trường output theo yêu cầu của schema
        if "error" in test_result and "output" not in test_result:
            # Nếu có lỗi và không có output, thêm trường output rỗng
            test_result["output"] = ""
            
            # Xác định status dựa trên error_type
            error_type = test_result.get("error_type", "error")
            test_result["status"] = error_type
            
            # Hiển thị lỗi cụ thể trong message
            test_result["message"] = test_result.get("error", "Lỗi không xác định")
        
        return test_result
        
    except Exception as e:
        logger.error(f"Error testing submission: {str(e)}")
        # Trả về đối tượng với trường output rỗng thay vì ném ra HTTPException
        error_message = str(e)
        error_type = type(e).__name__
        return {
            "output": "",
            "status": "error",
            "message": f"Lỗi {error_type}: {error_message}"
        }

@router.get("/", response_model=List[schemas.SubmissionWithDetails])
def read_submissions(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    problem_id: Optional[str] = None,
    contest_id: Optional[str] = None,
    user_id: Optional[str] = None,
    view_mode: Optional[str] = Query(None, enum=["all", "mine"]),
    status: Optional[str] = Query(None, enum=[
        "pending", "accepted", "wrong_answer", "time_limit_exceeded",
        "memory_limit_exceeded", "runtime_error", "compilation_error"
    ]),
    language: Optional[str] = Query(None, enum=["cpp", "python"]),
    current_user: models.User = Depends(deps.get_current_active_user),
    response: Response = None,  # Thêm tham số response
) -> Any:
    """
    Retrieve submissions.
    """
    # Xử lý view_mode
    if view_mode == 'mine' or (not current_user.is_admin and not user_id):
        user_id = current_user.id
    elif not current_user.is_admin and user_id and user_id != current_user.id:
        # Người dùng thông thường không thể xem submission của người khác
        user_id = current_user.id

    # Sử dụng user_id (đã được xử lý) trong truy vấn
    submissions = crud.submissions.get_multi(
        db, skip=skip, limit=limit, user_id=user_id, 
        problem_id=problem_id, contest_id=contest_id,
        status=status, language=language,
        view_mode=view_mode, current_user_id=current_user.id
    )
    
    # Tính toán tổng số kết quả để gửi x-total-count header
    total_count = crud.submissions.count(
        db, user_id=user_id, problem_id=problem_id,
        contest_id=contest_id, status=status, language=language,
        view_mode=view_mode, current_user_id=current_user.id
    )
    
    # Thêm header vào response
    if response:
        response.headers["X-Total-Count"] = str(total_count)
    
    # Bổ sung thông tin chi tiết cho mỗi submission
    result = []
    for sub in submissions:
        # Khởi tạo dictionary với giá trị mặc định cho status
        submission_data = {
            "status": "pending"  # Giá trị mặc định cho status
        }
        
        # Lấy các thuộc tính cơ bản từ submission
        for key in ["id", "user_id", "problem_id", "contest_id", "code", 
                   "language", "execution_time_ms", "memory_used_kb", 
                   "submitted_at"]:
            if hasattr(sub, key):
                submission_data[key] = getattr(sub, key)
        
        # Đặc biệt kiểm tra status để đảm bảo nó có giá trị hợp lệ
        if hasattr(sub, "status") and getattr(sub, "status"):
            submission_data["status"] = getattr(sub, "status")
        
        # Thêm các thông tin bổ sung
        submission_data["problem_title"] = sub.problem.title if sub.problem else None
        submission_data["username"] = sub.user.username if sub.user else None
        
        try:
            # Tạo đối tượng SubmissionWithDetails
            details = schemas.SubmissionWithDetails(**submission_data)
            result.append(details)
        except Exception as e:
            logger.error(f"Error creating SubmissionWithDetails: {e}")
            # Skip invalid submissions instead of failing the whole request
            continue
    
    return result

@router.get("/solved-problems", response_model=Dict[str, List[str]])
def get_user_solved_problems(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Lấy danh sách các bài toán mà người dùng đã giải thành công.
    """
    # Tìm tất cả các submissions thành công của user hiện tại
    solved_submissions = db.query(models.Submission).filter(
        models.Submission.user_id == current_user.id,
        models.Submission.status == "accepted"
    ).all()
    
    # Lấy danh sách các problem_id không trùng lặp
    solved_problem_ids = list(set([sub.problem_id for sub in solved_submissions]))
    
    return {"solved_problems": solved_problem_ids}

@router.post("/", response_model=schemas.Submission)
def create_submission(
    *,
    db: Session = Depends(deps.get_db),
    submission_in: schemas.SubmissionCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Tạo bài nộp mới.
    """
    try:
        # Kiểm tra bài toán tồn tại
        problem = db.query(models.Problem).filter(models.Problem.id == submission_in.problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy bài toán này",
            )
        
        # Kiểm tra quyền truy cập bài toán nếu là private
        if not problem.is_public and not current_user.is_admin and problem.created_by != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền truy cập bài toán này"
            )
        
        # Kiểm tra ngôn ngữ lập trình hỗ trợ
        language = db.query(models.Language).filter(
            models.Language.identifier == submission_in.language,
            models.Language.is_active == True
        ).first()
        
        if not language:
            raise HTTPException(
                status_code=400, 
                detail="Ngôn ngữ lập trình không được hỗ trợ"
            )
        
        # Nếu bài nộp cho cuộc thi, kiểm tra hợp lệ
        if submission_in.contest_id:
            contest = crud.contests.get_by_id(db, id=submission_in.contest_id)
            if not contest:
                raise HTTPException(
                    status_code=404,
                    detail="Không tìm thấy cuộc thi",
                )
            
            # Kiểm tra người dùng đã đăng ký cuộc thi
            participants = crud.contests.get_participants(db, contest_id=submission_in.contest_id)
            is_participant = any(p.user_id == current_user.id for p in participants)
            if not is_participant:
                raise HTTPException(
                    status_code=403,
                    detail="Bạn chưa đăng ký tham gia cuộc thi này",
                )
            
            # Kiểm tra cuộc thi đang diễn ra
            now = datetime.utcnow()
            if now < contest.start_time:
                raise HTTPException(
                    status_code=400,
                    detail="Cuộc thi chưa bắt đầu",
                )
            if now > contest.end_time:
                raise HTTPException(
                    status_code=400,
                    detail="Cuộc thi đã kết thúc",
                )
            
            # Kiểm tra bài toán thuộc cuộc thi
            contest_problems = [cp.problem_id for cp in contest.problems]
            if submission_in.problem_id not in contest_problems:
                raise HTTPException(
                    status_code=400,
                    detail="Bài toán này không thuộc cuộc thi",
                )
        
        # Tạo bài nộp
        submission = crud.submissions.create(db, obj_in=submission_in, user_id=current_user.id)
        
        # Chấm bài nộp
        try:
            judge_result = judge.judge_submission(db, submission)
            
            # Cập nhật kết quả chấm
            update_data = schemas.SubmissionUpdate(
                status=judge_result["status"],
                execution_time_ms=judge_result["execution_time_ms"],
                memory_used_kb=judge_result["memory_used_kb"],
                details=judge_result.get("details", None)  # Thêm chi tiết kết quả
            )
            submission = crud.submissions.update(db, db_obj=submission, obj_in=update_data)
            
            # Nếu là bài nộp cuộc thi và được chấp nhận, cập nhật điểm
            if submission.contest_id and submission.status == "accepted":
                # Tìm điểm bài toán
                contest_problem = next(
                    (cp for cp in contest.problems if cp.problem_id == submission.problem_id), 
                    None
                )
                if contest_problem:
                    # Cập nhật điểm người tham gia
                    crud.contests.update_score(
                        db, 
                        contest_id=submission.contest_id, 
                        user_id=current_user.id,
                        score=contest_problem.points
                    )
        except Exception as e:
            logger.error(f"Lỗi khi chấm bài nộp: {str(e)}")
            # Ghi lại thông tin lỗi chi tiết
            error_details = {
                "error_message": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Cập nhật trạng thái lỗi và chi tiết
            update_data = schemas.SubmissionUpdate(
                status="runtime_error",
                execution_time_ms=0,
                memory_used_kb=0,
                details={"error": str(e), "error_details": error_details}
            )
            submission = crud.submissions.update(db, db_obj=submission, obj_in=update_data)
        
        return submission
        
    except HTTPException as he:
        # Chuyển tiếp HTTP exceptions
        raise he
    except Exception as e:
        # Xử lý lỗi chung
        logger.error(f"Lỗi không xác định khi tạo bài nộp: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Có lỗi xảy ra khi xử lý bài nộp: {str(e)}"
        )
        
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
    # Kiểm tra submission_id có hợp lệ không
    if not submission_id or submission_id == "undefined":
        raise HTTPException(
            status_code=400,
            detail="ID bài nộp không hợp lệ",
        )
        
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