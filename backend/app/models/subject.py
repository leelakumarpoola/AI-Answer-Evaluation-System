from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, index=True, nullable=False)
    department = Column(String, nullable=True)
    class_section = Column(String, nullable=True)
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('code', 'class_section', 'professor_id', name='uq_subject_code_section_prof'),
    )

    # Relationships
    professor = relationship("Professor", back_populates="subjects")
    exams = relationship("Exam", back_populates="subject", cascade="all, delete-orphan")
