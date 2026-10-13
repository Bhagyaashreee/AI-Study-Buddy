import json
from datetime import datetime
from typing import List, Optional, Any
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.session import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="processing")
    status_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index")
    quizzes = relationship("Quiz", back_populates="document", cascade="all, delete-orphan")
    flashcards = relationship("Flashcard", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("idx_doc_chunk", "document_id", "chunk_index"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index}, page={self.page_number})>"


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    difficulty = Column(String(50), nullable=False, default="Medium")
    total_questions = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan", order_by="desc(QuizAttempt.completed_at)")

    def __repr__(self) -> str:
        return f"<Quiz(id={self.id}, title='{self.title}', difficulty='{self.difficulty}')>"


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)  # JSON-encoded array of options
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)
    page_reference = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="questions")

    @property
    def options(self) -> List[str]:
        try:
            return json.loads(self.options_json)
        except Exception:
            return []

    @options.setter
    def options(self, value: List[str]) -> None:
        self.options_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<QuizQuestion(id={self.id}, quiz_id={self.quiz_id})>"


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    percentage = Column(Float, nullable=False)
    user_answers_json = Column(Text, nullable=False, default="{}")  # JSON-encoded dict of answers
    completed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    quiz = relationship("Quiz", back_populates="attempts")

    @property
    def user_answers(self) -> dict:
        try:
            return json.loads(self.user_answers_json)
        except Exception:
            return {}

    @user_answers.setter
    def user_answers(self, value: dict) -> None:
        self.user_answers_json = json.dumps(value)

    def __repr__(self) -> str:
        return f"<QuizAttempt(id={self.id}, quiz_id={self.quiz_id}, score={self.score}/{self.total_questions})>"


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    difficulty_rating = Column(String(50), nullable=False, default="Medium")  # Easy, Medium, Hard
    page_reference = Column(Integer, nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    next_review_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    document = relationship("Document", back_populates="flashcards")

    def __repr__(self) -> str:
        return f"<Flashcard(id={self.id}, doc_id={self.document_id}, difficulty='{self.difficulty_rating}')>"
