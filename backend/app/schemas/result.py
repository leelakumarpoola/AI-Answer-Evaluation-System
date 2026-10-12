from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class QuestionResultSchema(BaseModel):
    question_number: str
    question_text: str
    maximum_marks: float
    ai_suggested_marks: Optional[float] = None
    final_marks: Optional[float] = None
    professor_remarks: Optional[str] = None
    ai_feedback: Optional[str] = None
    review_status: str

class ExamResultSchema(BaseModel):
    student_name: str
    roll_number: str
    subject: str
    course_code: str
    exam_name: str
    exam_date: Optional[datetime] = None
    total_marks: float
    maximum_marks: float
    percentage: float
    status: str
    questions: List[QuestionResultSchema]

class StudentResultSummarySchema(BaseModel):
    student_id: int
    answer_script_id: int
    student_name: str
    roll_number: str
    total_marks: float
    maximum_marks: float
    percentage: float
    status: str
