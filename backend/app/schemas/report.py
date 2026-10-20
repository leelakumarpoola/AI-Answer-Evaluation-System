from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

class ExamSummaryResponse(BaseModel):
    exam_id: int
    exam_name: str
    subject_name: str
    course_code: str
    exam_date: Optional[datetime] = None
    maximum_marks: float
    
    total_students: int
    students_with_answer_scripts: int
    students_completed: int
    students_pending: int
    
    total_evaluations: int
    approved_evaluations: int
    pending_evaluations: int
    
    average_marks: Optional[float] = None
    highest_marks: Optional[float] = None
    lowest_marks: Optional[float] = None
    median_marks: Optional[float] = None
    average_percentage: Optional[float] = None

class StudentPerformanceResponse(BaseModel):
    student_id: Optional[int] = None
    student_name: str
    roll_number: str
    email: Optional[str] = None
    total_marks: float
    maximum_marks: float
    percentage: float
    result_status: str
    ai_suggested_marks: Optional[float] = None
    answer_script_id: Optional[int] = None
    evaluation_stage: Optional[str] = None  # 'approved', 'ai_evaluated', 'script_uploaded', 'not_submitted'

class QuestionPerformanceResponse(BaseModel):
    question_number: str
    question_text: str
    maximum_marks: float
    
    students_evaluated: int
    average_marks: Optional[float] = None
    highest_marks: Optional[float] = None
    lowest_marks: Optional[float] = None
    average_percentage: Optional[float] = None
    performance_category: Optional[str] = None

class MarksDistributionResponse(BaseModel):
    distribution: Dict[str, int]

class CompletionReportResponse(BaseModel):
    total_students: int
    answer_scripts_uploaded: int
    answer_scripts_processed: int
    students_with_extracted_answers: int
    students_with_approved_results: int
    students_pending_review: int
