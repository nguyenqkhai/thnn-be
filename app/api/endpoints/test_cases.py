from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.db.session import get_db
from app import models, schemas
from app.api import deps

router = APIRouter()

@router.get("/{problem_id}/testcases", response_model=List[schemas.TestCase])
async def get_test_cases(
    problem_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Lấy danh sách test cases của một bài toán
    """
    # Kiểm tra quyền truy cập (chỉ admin hoặc người tạo bài toán)
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài toán")
    
    is_admin = current_user.is_admin
    is_owner = problem.created_by == current_user.id
    
    if not (is_admin or is_owner):
        # Người dùng thông thường chỉ thấy các test case mẫu
        test_cases = db.query(models.TestCase).filter(
            models.TestCase.problem_id == problem_id,
            models.TestCase.is_sample == True
        ).order_by(models.TestCase.order).all()
    else:
        # Admin hoặc người tạo bài thấy tất cả
        test_cases = db.query(models.TestCase).filter(
            models.TestCase.problem_id == problem_id
        ).order_by(models.TestCase.order).all()
    
    return test_cases

@router.post("/{problem_id}/testcases", response_model=schemas.TestCase)
async def create_test_case(
    test_case: schemas.TestCaseCreate,
    problem_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Tạo test case mới cho bài toán
    """
    # Kiểm tra quyền truy cập (chỉ admin hoặc người tạo bài toán)
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài toán")
    
    is_admin = current_user.is_admin
    is_owner = problem.created_by == current_user.id
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Không có quyền thêm test case")
    
    # Xác định thứ tự tiếp theo nếu không được cung cấp
    if test_case.order is None:
        max_order = db.query(models.TestCase.order).filter(
            models.TestCase.problem_id == problem_id
        ).order_by(models.TestCase.order.desc()).first()
        
        next_order = 1
        if max_order:
            next_order = max_order[0] + 1
        
        test_case_data = test_case.dict()
        test_case_data["order"] = next_order
    else:
        test_case_data = test_case.dict()
    
    # Tạo test case mới
    db_test_case = models.TestCase(
        id=str(uuid.uuid4()),
        problem_id=problem_id,
        **test_case_data
    )
    
    db.add(db_test_case)
    db.commit()
    db.refresh(db_test_case)
    
    return db_test_case

@router.put("/{problem_id}/testcases/{testcase_id}", response_model=schemas.TestCase)
async def update_test_case(
    test_case_update: schemas.TestCaseCreate,
    problem_id: str = Path(...),
    testcase_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Cập nhật test case
    """
    # Kiểm tra quyền truy cập
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài toán")
    
    is_admin = current_user.is_admin
    is_owner = problem.created_by == current_user.id
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Không có quyền cập nhật test case")
    
    # Tìm test case
    test_case = db.query(models.TestCase).filter(
        models.TestCase.id == testcase_id,
        models.TestCase.problem_id == problem_id
    ).first()
    
    if not test_case:
        raise HTTPException(status_code=404, detail="Không tìm thấy test case")
    
    # Cập nhật thông tin
    update_data = test_case_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(test_case, key, value)
    
    db.commit()
    db.refresh(test_case)
    
    return test_case

@router.delete("/{problem_id}/testcases/{testcase_id}", response_model=schemas.Message)
async def delete_test_case(
    problem_id: str = Path(...),
    testcase_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    """
    Xóa test case
    """
    # Kiểm tra quyền truy cập
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Không tìm thấy bài toán")
    
    is_admin = current_user.is_admin
    is_owner = problem.created_by == current_user.id
    
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Không có quyền xóa test case")
    
    # Tìm và xóa test case
    test_case = db.query(models.TestCase).filter(
        models.TestCase.id == testcase_id,
        models.TestCase.problem_id == problem_id
    ).first()
    
    if not test_case:
        raise HTTPException(status_code=404, detail="Không tìm thấy test case")
    
    db.delete(test_case)
    db.commit()
    
    return {"message": "Đã xóa test case thành công"}