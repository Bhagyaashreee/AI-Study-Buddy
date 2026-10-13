from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class QuizGenerateRequest(BaseModel):
    """Request model for generating an AI quiz."""
    document_ids: List[int] = Field(
        ...,
        min_length=1,
        description="One or more document IDs to generate the quiz from."
    )
    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional title for the quiz."
    )
    difficulty: str = Field(
        default="Medium",
        description="Difficulty level: 'Easy', 'Medium', or 'Hard'."
    )
    num_questions: int = Field(
        default=3,
        ge=1,
        le=20,
        description="Number of multiple choice questions to generate."
    )

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        clean = v.capitalize()
        if clean not in ["Easy", "Medium", "Hard"]:
            raise ValueError("Difficulty must be 'Easy', 'Medium', or 'Hard'.")
        return clean


class QuizQuestionPublicResponse(BaseModel):
    """Public question format when taking a quiz (correct answer is hidden)."""
    id: int
    quiz_id: int
    question_text: str
    options: List[str]
    page_reference: Optional[int] = None


class QuizQuestionFullResponse(BaseModel):
    """Full question format including answer and explanation for review."""
    id: int
    quiz_id: int
    question_text: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None
    page_reference: Optional[int] = None


class QuizResponse(BaseModel):
    """Quiz response for student to solve."""
    id: int
    title: str
    difficulty: str
    total_questions: int
    document_id: Optional[int] = None
    created_at: datetime
    questions: List[QuizQuestionPublicResponse]


class QuizListItemResponse(BaseModel):
    """Summary item for quiz listing."""
    id: int
    title: str
    difficulty: str
    total_questions: int
    document_id: Optional[int] = None
    created_at: datetime
    attempts_count: int = 0
    best_percentage: Optional[float] = None


class QuizListResponse(BaseModel):
    """List of all generated quizzes."""
    quizzes: List[QuizListItemResponse]
    total_quizzes: int


class QuizSubmitRequest(BaseModel):
    """Submission payload containing student's chosen answers."""
    # Maps question_id (as string or int) -> selected option text
    answers: Dict[str, str] = Field(
        ...,
        description="Mapping of question IDs to student's chosen option text."
    )


class QuestionResultItem(BaseModel):
    """Graded result for an individual quiz question."""
    question_id: int
    question_text: str
    selected_answer: Optional[str] = None
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None
    page_reference: Optional[int] = None


class QuizSubmitResponse(BaseModel):
    """Scored results returned after quiz submission."""
    attempt_id: int
    quiz_id: int
    score: int
    total_questions: int
    percentage: float
    completed_at: datetime
    results: List[QuestionResultItem]


class QuizAttemptResponse(BaseModel):
    """Quiz attempt history record."""
    id: int
    quiz_id: int
    score: int
    total_questions: int
    percentage: float
    completed_at: datetime
