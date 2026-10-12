from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("exam_documents.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String, nullable=False)
    extracted_text = Column(String, nullable=True)
    ocr_status = Column(String, default="pending")
    ocr_confidence = Column(Float, nullable=True)
    error_message = Column(String, nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    document = relationship("ExamDocument")
