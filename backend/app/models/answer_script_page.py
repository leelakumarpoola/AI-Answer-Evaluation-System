from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class AnswerScriptPage(Base):
    __tablename__ = "answer_script_pages"

    id = Column(Integer, primary_key=True, index=True)
    answer_script_id = Column(Integer, ForeignKey("answer_scripts.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    image_path = Column(String, nullable=False)
    extracted_text = Column(String, nullable=True)
    ocr_status = Column(String, default="pending")
    ocr_confidence = Column(Float, nullable=True)
    error_message = Column(String, nullable=True)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    answer_script = relationship("AnswerScript", back_populates="pages")
