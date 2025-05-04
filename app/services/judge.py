from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import random
import time
import os
import tempfile
import subprocess
import shutil
import platform
import sys
from datetime import datetime
import uuid
import logging

from app.models.submissions import Submission
# Sửa đổi: Không import SubmissionTestResult từ models nếu nó không tồn tại
# from app.models.submissions import Submission, SubmissionTestResult
from app.schemas.submissions import SubmissionTestResult as SubmissionTestResultSchema
from app.models.problems import Problem, TestCase
from app.models.languages import Language
from app.models.judge_servers import JudgeServer
from app.crud import problems as problems_crud

logger = logging.getLogger(__name__)

# Cấu hình đường dẫn trình biên dịch
CPP_COMPILER_PATH = "C:\\UTE\\mingw64\\bin\\g++.exe"
PYTHON_INTERPRETER = "python"

def get_language_config(db: Session, language_identifier: str):
    """Lấy cấu hình ngôn ngữ từ database"""
    language = db.query(Language).filter(
        Language.identifier == language_identifier
    ).first()
    return language

def prepare_code_file(code: str, language_config):
    """Tạo file code tạm thời"""
    # Tạo thư mục tạm thời
    tmp_dir = tempfile.mkdtemp(prefix="judge_")
    file_name = f"main.{language_config.file_extension}"
    file_path = os.path.join(tmp_dir, file_name)
    
    # Ghi code vào file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)
    
    logger.info(f"Created temp file at: {file_path}")
    
    return {
        "dir": tmp_dir,
        "file_path": file_path,
        "file_name": file_name
    }

def compile_code(code_info, language_config):
    """Biên dịch code nếu cần"""
    if not language_config.compile_command:
        logger.info(f"Language {language_config.identifier} does not need compilation")
        return {"success": True, "message": "Ngôn ngữ không cần biên dịch"}
    
    # Xác định đường dẫn file thực thi
    exe_path = os.path.join(code_info["dir"], "main")
    if platform.system() == "Windows" and language_config.identifier == 'cpp':
        exe_path += ".exe"
    
    # Xử lý lệnh biên dịch tùy thuộc vào ngôn ngữ
    if language_config.identifier == 'cpp':
        # Sử dụng lệnh biên dịch cụ thể cho C++
        compile_command = f'"{CPP_COMPILER_PATH}" -std=c++17 -O2 -o "{exe_path}" "{code_info["file_path"]}"'
    else:
        # Sử dụng lệnh biên dịch từ database
        compile_command = language_config.compile_command
        compile_command = compile_command.replace("{file_path}", code_info["file_path"])
        compile_command = compile_command.replace("{exe_path}", exe_path)
        compile_command = compile_command.replace("{dir_path}", code_info["dir"])
    
    # Log thông tin để debug
    logger.info(f"Compile command: {compile_command}")
    logger.info(f"Working directory: {code_info['dir']}")
    
    try:
        # Kiểm tra file source tồn tại
        if not os.path.exists(code_info["file_path"]):
            logger.error(f"Source file not found: {code_info['file_path']}")
            return {
                "success": False,
                "message": "Lỗi: Không tìm thấy file source code",
                "output": f"Không tìm thấy file source code"
            }
        
        # Ghi ra nội dung code để debug
        try:
            with open(code_info["file_path"], "r", encoding="utf-8") as f:
                source_content = f.read()
                logger.info(f"Source code content (first 100 chars): {source_content[:100]}...")
        except Exception as e:
            logger.error(f"Error reading source file: {str(e)}")
        
        # Thực thi lệnh biên dịch
        process = subprocess.Popen(
            compile_command,
            shell=True,
            cwd=code_info["dir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            errors='replace'  # Tránh lỗi Unicode
        )
        
        # Lấy output của quá trình biên dịch
        stdout, stderr = process.communicate(timeout=20)
        
        # Log output của quá trình biên dịch
        logger.info(f"Compile process return code: {process.returncode}")
        logger.info(f"Compile stdout: {stdout}")
        logger.info(f"Compile stderr: {stderr}")
        
        # Kiểm tra kết quả biên dịch
        if process.returncode != 0:
            logger.error(f"Compilation failed with return code {process.returncode}")
            return {
                "success": False,
                "message": "Lỗi biên dịch",
                "output": stderr or "Unknown compilation error"
            }
        
        # Kiểm tra file thực thi đã được tạo
        if not os.path.exists(exe_path):
            logger.error(f"Executable file not found after compilation: {exe_path}")
            return {
                "success": False,
                "message": "Biên dịch không tạo được file thực thi",
                "output": "Không tìm thấy file thực thi sau khi biên dịch"
            }
        
        logger.info(f"Compilation successful, executable created at: {exe_path}")
        return {
            "success": True, 
            "message": "Biên dịch thành công",
            "executable": exe_path
        }
        
    except subprocess.TimeoutExpired:
        # Nếu quá trình biên dịch bị timeout
        try:
            process.kill()
        except:
            pass
        
        logger.error("Compilation process timed out")
        return {
            "success": False,
            "message": "Quá thời gian biên dịch",
            "output": "Quá trình biên dịch bị timeout"
        }
    except Exception as e:
        # Xử lý các lỗi khác
        logger.error(f"Exception during compilation: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Lỗi không xác định khi biên dịch: {str(e)}",
            "output": str(e)
        }

def run_code_with_input(code_info, language_config, input_text, time_limit_ms=1000):
    """Chạy code với input cụ thể"""
    # Xác định đường dẫn file thực thi
    exe_path = os.path.join(code_info["dir"], "main")
    if platform.system() == "Windows" and language_config.identifier == 'cpp':
        exe_path += ".exe"
    
    # Xử lý lệnh chạy tùy thuộc vào ngôn ngữ
    if language_config.identifier == 'cpp':
        if platform.system() == "Windows":
            # Trên Windows, chạy trực tiếp file thực thi
            run_command = f'"{exe_path}"'
        else:
            # Trên Unix, thêm ./ phía trước
            run_command = f'"./{exe_path}"'
    elif language_config.identifier == 'python':
        # Đối với Python, sử dụng trực tiếp interpreter
        run_command = f'{PYTHON_INTERPRETER} "{code_info["file_path"]}"'
    else:
        # Sử dụng lệnh chạy từ database
        run_command = language_config.run_command
        run_command = run_command.replace("{file_path}", code_info["file_path"])
        run_command = run_command.replace("{exe_path}", exe_path)
        run_command = run_command.replace("{dir_path}", code_info["dir"])
    
    # Log thông tin để debug
    logger.info(f"Run command: {run_command}")
    logger.info(f"Working directory: {code_info['dir']}")
    logger.info(f"Input (first 100 chars): {input_text[:100]}...")
    
    # Ghi input vào file
    input_file = os.path.join(code_info["dir"], "input.txt")
    with open(input_file, "w", encoding="utf-8") as f:
        f.write(input_text)
    
    try:
        # Kiểm tra file thực thi tồn tại (chỉ với các ngôn ngữ biên dịch)
        if language_config.compile_command and not os.path.exists(exe_path):
            logger.error(f"Executable file not found: {exe_path}")
            return {
                "success": False,
                "message": "Lỗi: Không tìm thấy file thực thi",
                "output": f"Không tìm thấy file thực thi: {exe_path}",
                "execution_time_ms": 0,
                "memory_used_kb": 0
            }
        
        start_time = time.time()
        
        # Mở file input để đọc
        with open(input_file, "r", encoding="utf-8") as f:
            # Thực thi lệnh chạy
            process = subprocess.Popen(
                run_command,
                shell=True,
                cwd=code_info["dir"],
                stdin=f,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                errors='replace'  # Tránh lỗi Unicode
            )
            
            # Lấy output với timeout
            timeout_seconds = max(1, time_limit_ms / 1000 + 0.5)  # Tối thiểu 1 giây
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        
        end_time = time.time()
        execution_time_ms = int((end_time - start_time) * 1000)
        
        # Log output của quá trình chạy
        logger.info(f"Run process return code: {process.returncode}")
        logger.info(f"Run stdout: {stdout}")
        logger.info(f"Run stderr: {stderr}")
        logger.info(f"Execution time: {execution_time_ms}ms")
        
        # Đo bộ nhớ sử dụng (giả lập)
        memory_used_kb = random.randint(1000, 10000)
        
        # Kiểm tra kết quả chạy
        if process.returncode != 0:
            logger.error(f"Runtime error with return code {process.returncode}")
            return {
                "success": False,
                "message": "Lỗi runtime",
                "output": stderr or "Unknown runtime error",
                "execution_time_ms": execution_time_ms,
                "memory_used_kb": memory_used_kb
            }
        
        logger.info(f"Execution successful in {execution_time_ms}ms")
        return {
            "success": True,
            "message": "Thực thi thành công",
            "output": stdout,
            "execution_time_ms": execution_time_ms,
            "memory_used_kb": memory_used_kb
        }
        
    except subprocess.TimeoutExpired:
        # Nếu quá trình chạy bị timeout
        try:
            process.kill()
        except:
            pass
        
        logger.error(f"Execution timed out after {time_limit_ms}ms")
        return {
            "success": False,
            "message": "Quá thời gian thực thi",
            "output": "Quá trình thực thi bị timeout",
            "execution_time_ms": time_limit_ms,
            "memory_used_kb": memory_used_kb
        }
    except Exception as e:
        # Xử lý các lỗi khác
        logger.error(f"Exception during execution: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Lỗi không xác định khi chạy code: {str(e)}",
            "output": str(e),
            "execution_time_ms": 0,
            "memory_used_kb": 0
        }

def is_output_correct(expected: str, actual: str) -> bool:
    """Kiểm tra output có đúng không, bỏ qua whitespace ở cuối"""
    # Chuẩn hóa chuỗi để so sánh
    expected_lines = expected.rstrip().split("\n")
    actual_lines = actual.rstrip().split("\n")
    
    # Kiểm tra số dòng
    if len(expected_lines) != len(actual_lines):
        logger.info(f"Output line count mismatch: expected {len(expected_lines)}, got {len(actual_lines)}")
        return False
    
    # So sánh từng dòng
    for i in range(len(expected_lines)):
        if expected_lines[i].rstrip() != actual_lines[i].rstrip():
            logger.info(f"Output mismatch at line {i+1}:")
            logger.info(f"Expected: '{expected_lines[i].rstrip()}'")
            logger.info(f"Actual: '{actual_lines[i].rstrip()}'")
            return False
    
    logger.info("Output matches expected result")
    return True

def judge_submission(db: Session, submission: Submission) -> Dict[str, Any]:
    """
    Chấm điểm một bài nộp thực tế bằng cách chạy code qua từng test case
    """
    logger.info(f"Starting judging submission ID: {submission.id}")
    
    try:
        # Lấy bài toán và các test case
        problem = problems_crud.get_by_id_with_test_cases(db, id=submission.problem_id)
        if not problem:
            logger.error(f"Problem not found: {submission.problem_id}")
            return {
                "status": "judge_error",
                "execution_time_ms": 0,
                "memory_used_kb": 0,
                "message": "Không tìm thấy bài toán"
            }
        
        # Lấy thông tin ngôn ngữ
        language_config = get_language_config(db, submission.language)
        if not language_config:
            logger.error(f"Language not supported: {submission.language}")
            return {
                "status": "judge_error",
                "execution_time_ms": 0,
                "memory_used_kb": 0,
                "message": "Không hỗ trợ ngôn ngữ này"
            }
        
        logger.info(f"Judging submission for problem: {problem.title}, language: {language_config.name}")
        
        # Chuẩn bị file code
        code_info = prepare_code_file(submission.code, language_config)
        
        try:
            # Biên dịch code nếu cần
            if language_config.compile_command:
                logger.info(f"Compiling code for language: {language_config.name}")
                compile_result = compile_code(code_info, language_config)
                
                if not compile_result["success"]:
                    logger.error(f"Compilation failed: {compile_result['message']}")
                    return {
                        "status": "compilation_error",
                        "execution_time_ms": 0,
                        "memory_used_kb": 0,
                        "message": compile_result.get("output", "Lỗi biên dịch")
                    }
                logger.info("Compilation successful")
            
            # Lấy các test case
            test_cases = db.query(TestCase).filter(
                TestCase.problem_id == problem.id
            ).order_by(TestCase.order).all()
            
            if not test_cases:
                logger.error(f"No test cases found for problem: {problem.id}")
                return {
                    "status": "judge_error",
                    "execution_time_ms": 0,
                    "memory_used_kb": 0,
                    "message": "Không có test case nào cho bài toán này"
                }
            
            logger.info(f"Found {len(test_cases)} test cases")
            
            # Chạy từng test case
            results = []
            max_execution_time = 0
            max_memory_used = 0
            
            for test_case in test_cases:
                logger.info(f"Running test case #{test_case.order}")
                
                # Xác định giới hạn thời gian
                time_limit = getattr(test_case, 'time_limit_ms', None) or problem.time_limit_ms
                
                # Chạy code với input của test case
                run_result = run_code_with_input(
                    code_info,
                    language_config,
                    test_case.input,
                    time_limit
                )
                
                # Xử lý kết quả chạy
                if not run_result["success"]:
                    # Xác định loại lỗi
                    status = "time_limit_exceeded" if "thời gian" in run_result.get("message", "").lower() else "runtime_error"
                    
                    # Lưu kết quả test case - bỏ qua nếu không có model SubmissionTestResult
                    logger.info(f"Test case #{test_case.order} failed: {status}")
                    
                    # Trả về kết quả lỗi
                    return {
                        "status": status,
                        "execution_time_ms": run_result.get("execution_time_ms", 0),
                        "memory_used_kb": run_result.get("memory_used_kb", 0),
                        "message": f"{run_result.get('message', '')} ở test case #{test_case.order}"
                    }
                
                # So sánh output với expected output
                if not is_output_correct(test_case.expected_output, run_result["output"]):
                    # Lưu kết quả test case sai - bỏ qua nếu không có model SubmissionTestResult
                    logger.info(f"Test case #{test_case.order} failed: wrong_answer")
                    
                    # Trả về kết quả wrong answer
                    return {
                        "status": "wrong_answer",
                        "execution_time_ms": run_result["execution_time_ms"],
                        "memory_used_kb": run_result["memory_used_kb"],
                        "message": f"Kết quả sai ở test case #{test_case.order}"
                    }
                
                # Kiểm tra memory limit
                memory_limit = getattr(test_case, 'memory_limit_kb', None) or problem.memory_limit_kb
                if run_result["memory_used_kb"] > memory_limit:
                    # Lưu kết quả test case vượt bộ nhớ - bỏ qua nếu không có model SubmissionTestResult
                    logger.info(f"Test case #{test_case.order} failed: memory_limit_exceeded")
                    
                    # Trả về kết quả memory limit exceeded
                    return {
                        "status": "memory_limit_exceeded",
                        "execution_time_ms": run_result["execution_time_ms"],
                        "memory_used_kb": run_result["memory_used_kb"],
                        "message": f"Vượt quá giới hạn bộ nhớ ở test case #{test_case.order}"
                    }
                
                # Lưu kết quả test case thành công - bỏ qua nếu không có model SubmissionTestResult
                logger.info(f"Test case #{test_case.order} passed")
                
                # Cập nhật thời gian và bộ nhớ max
                max_execution_time = max(max_execution_time, run_result["execution_time_ms"])
                max_memory_used = max(max_memory_used, run_result["memory_used_kb"])
                
                # Thêm kết quả vào danh sách
                results.append({
                    "test_case_id": test_case.id,
                    "test_case_order": test_case.order,
                    "status": "accepted",
                    "execution_time_ms": run_result["execution_time_ms"],
                    "memory_used_kb": run_result["memory_used_kb"]
                })
            
            # Tất cả test case đều đúng
            logger.info(f"All test cases passed: {len(test_cases)}/{len(test_cases)}")
            return {
                "status": "accepted",
                "execution_time_ms": max_execution_time,
                "memory_used_kb": max_memory_used,
                "message": "Tất cả test case đều đúng"
            }
        
        finally:
            # Dọn dẹp tài nguyên
            try:
                logger.info(f"Cleaning up temporary directory: {code_info['dir']}")
                shutil.rmtree(code_info["dir"])
            except Exception as e:
                logger.error(f"Error cleaning up temp directory: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in judge_submission: {str(e)}", exc_info=True)
        return {
            "status": "judge_error",
            "execution_time_ms": 0,
            "memory_used_kb": 0,
            "message": f"Lỗi hệ thống: {str(e)}"
        }

async def test_code(
    user_id: str,
    problem_id: str,
    code: str,
    language_id: str,
    input: str,
    db: Session
) -> Dict[str, Any]:
    """
    Test code với input tùy chỉnh.
    """
    try:
        # Lấy thông tin ngôn ngữ
        language = db.query(Language).filter(Language.id == language_id).first()
        if not language:
            return {
                "error": "Ngôn ngữ không tồn tại"
            }
        
        # Chuẩn bị code file
        code_info = prepare_code_file(code, language)
        
        # Biên dịch code nếu cần
        if language.compile_command:
            compile_result = compile_code(code_info, language)
            if not compile_result["success"]:
                return {
                    "error": compile_result["message"]
                }
        
        # Chạy code với input
        run_result = run_code_with_input(code_info, language, input)
        
        # Dọn dẹp thư mục tạm
        try:
            shutil.rmtree(code_info["dir"])
        except:
            pass
        
        # Nếu chạy thành công, trả về output
        if run_result["success"]:
            return {
                "output": run_result["output"]
            }
        # Nếu có lỗi, trả về thông báo lỗi
        else:
            return {
                "error": run_result["message"]
            }
        
    except Exception as e:
        logger.error(f"Error testing code: {str(e)}")
        return {
            "error": str(e)
        }