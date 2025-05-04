from app.schemas.users import User, UserCreate, UserUpdate, Token, TokenPayload
from app.schemas.problems import Problem, ProblemCreate, ProblemUpdate, TestCase as ProblemTestCase, TestCaseCreate as ProblemTestCaseCreate, ProblemWithTestCases
from app.schemas.contests import Contest, ContestCreate, ContestUpdate, ContestProblem, ContestParticipant, ContestDetail
from app.schemas.submissions import (
    Submission, SubmissionCreate, SubmissionUpdate, SubmissionWithDetails, SubmissionTestInput, SubmissionTestResult
)
from app.schemas.test_cases import TestCase, TestCaseCreate, Message

# Export tất cả schemas
__all__ = [
    "User", "UserCreate", "UserUpdate", "Token", "TokenPayload",
    "Problem", "ProblemCreate", "ProblemUpdate", "ProblemTestCase", "ProblemTestCaseCreate", "ProblemWithTestCases",
    "Contest", "ContestCreate", "ContestUpdate", "ContestProblem", "ContestParticipant", "ContestDetail",
    "Submission", "SubmissionCreate", "SubmissionUpdate", "SubmissionWithDetails", "SubmissionTestInput", "SubmissionTestResult",
    "TestCase", "TestCaseCreate", "Message"
]