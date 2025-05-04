from fastapi import APIRouter
from app.api.endpoints import users, auth, problems, contests, submissions, test_cases

api_router = APIRouter()

# Include các router con
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(problems.router, prefix="/problems", tags=["problems"])
api_router.include_router(contests.router, prefix="/contests", tags=["contests"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(test_cases.router, prefix="/problems", tags=["test_cases"])