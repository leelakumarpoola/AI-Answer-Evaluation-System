from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    student_answer_id = Column(Integer, ForeignKey("student_answers.id"), nullable=False, unique=True)
    awarded_marks = Column(Float, nullable=True)
    max_marks = Column(Float, nullable=True)
    similarity_score = Column(Float, nullable=True)
    evaluation_status = Column(String, nullable=True)
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    
    final_marks = Column(Float, nullable=True)
    professor_remarks = Column(String, nullable=True)
    review_status = Column(String, default="ai_evaluated", nullable=False)
    reviewed_by = Column(Integer, ForeignKey("professors.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    diagram_data = Column(String, nullable=True)

    # Relationships
    student_answer = relationship("StudentAnswer", back_populates="evaluation")
    feedback = relationship("Feedback", back_populates="evaluation", cascade="all, delete-orphan")
