from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class DocumentType(str, enum.Enum):
    question_paper = "question_paper"
    model_answer = "model_answer"
    marks_rubric = "marks_rubric"

class ExamDocument(Base):
    __tablename__ = "exam_documents"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_status = Column(String, default="uploaded")
    processing_status = Column(String, default="uploaded")
    page_count = Column(Integer, default=0)
    processed_page_count = Column(Integer, default=0)
    processing_error = Column(String, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    exam = relationship("Exam", back_populates="documents")
