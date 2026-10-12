from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class AnswerScript(Base):
    __tablename__ = "answer_scripts"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    upload_status = Column(String, default="uploaded")
    processing_status = Column(String, default="pending")
    ocr_status = Column(String, default="pending")
    page_count = Column(Integer, default=0)
    processing_error = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("Student", back_populates="answer_scripts")
    exam = relationship("Exam", back_populates="answer_scripts")
    student_answers = relationship("StudentAnswer", back_populates="answer_script", cascade="all, delete-orphan")
    pages = relationship("AnswerScriptPage", back_populates="answer_script", cascade="all, delete-orphan")
