from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    exam_type = Column(String, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    exam_date = Column(Date, nullable=True)
    total_marks = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subject = relationship("Subject", back_populates="exams")
    professor = relationship("Professor", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    answer_scripts = relationship("AnswerScript", back_populates="exam", cascade="all, delete-orphan")
    documents = relationship("ExamDocument", back_populates="exam", cascade="all, delete-orphan")
