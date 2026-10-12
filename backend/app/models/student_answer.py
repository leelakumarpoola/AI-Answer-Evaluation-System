from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)
    answer_script_id = Column(Integer, ForeignKey("answer_scripts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)
    start_page = Column(Integer, nullable=True)
    end_page = Column(Integer, nullable=True)
    answer_status = Column(String, default="detected")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    answer_script = relationship("AnswerScript", back_populates="student_answers")
    question = relationship("Question", back_populates="student_answers")
    evaluation = relationship("Evaluation", back_populates="student_answer", uselist=False, cascade="all, delete-orphan")
