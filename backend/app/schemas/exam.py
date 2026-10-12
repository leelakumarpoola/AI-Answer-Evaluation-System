from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, date

class ExamBase(BaseModel):
    name: str
    exam_type: str
    subject_id: int
    exam_date: Optional[date] = None
    total_marks: int
    duration_minutes: Optional[int] = None

    @field_validator('total_marks')
    @classmethod
    def validate_total_marks(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Total marks must be greater than zero')
        return v
        
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration_minutes(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError('Duration must be greater than zero')
        return v

class ExamCreate(ExamBase):
    pass

class ExamResponse(ExamBase):
    id: int
    professor_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
