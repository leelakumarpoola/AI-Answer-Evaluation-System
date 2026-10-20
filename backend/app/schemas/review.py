from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ReviewUpdateRequest(BaseModel):
    final_marks: float
    professor_remarks: Optional[str] = None

class StudentInfoSchema(BaseModel):
    name: str
    roll_number: str
    department: str
    year: int
    section: Optional[str] = None

class ExamInfoSchema(BaseModel):
    subject_name: str
    course_code: str
    exam_name: str
    exam_date: Optional[datetime] = None

class QuestionInfoSchema(BaseModel):
    question_number: int
    question_text: str
    max_marks: float

class StudentAnswerInfoSchema(BaseModel):
    answer_text: str
    page_range: Optional[str] = None

class ModelAnswerInfoSchema(BaseModel):
    answer_text: str

class RubricInfoSchema(BaseModel):
    criterion: str
    description: Optional[str] = None
    max_marks: float

class CriterionEvaluationSchema(BaseModel):
    criterion: str
    evidence_score: float
    suggested_marks: float
    reason: Optional[str] = None

class DiagramEvaluationSchema(BaseModel):
    diagram_detected: bool = False
    diagram_type: Optional[str] = None
    diagram_crop_url: Optional[str] = None
    page_number: Optional[int] = None
    bounding_box: Optional[List[int]] = None
    model_components: List[str] = []
    student_components: List[str] = []
    matching_components: List[str] = []
    missing_components: List[str] = []
    connectivity_errors: List[str] = []
    reversed_arrows: List[str] = []
    text_diagram_inconsistencies: List[str] = []
    has_contradiction: bool = False
    needs_review: bool = False
    review_reason: Optional[str] = None
    justification: Optional[str] = None
    suggested_marks: Optional[float] = None
    max_marks: Optional[float] = None

class AIEvaluationSchema(BaseModel):
    similarity_score: Optional[float] = None
    criterion_evaluations: List[CriterionEvaluationSchema]
    ai_suggested_marks: Optional[float] = None
    ai_feedback: Optional[str] = None
    diagram_evaluation: Optional[DiagramEvaluationSchema] = None

class ProfessorReviewSchema(BaseModel):
    final_marks: Optional[float] = None
    professor_remarks: Optional[str] = None
    review_status: str
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

class FullReviewPackageResponse(BaseModel):
    evaluation_id: int
    student_info: StudentInfoSchema
    exam_info: ExamInfoSchema
    question_info: QuestionInfoSchema
    student_answer_info: StudentAnswerInfoSchema
    model_answer_info: Optional[ModelAnswerInfoSchema] = None
    rubrics: List[RubricInfoSchema]
    ai_evaluation: AIEvaluationSchema
    professor_review: ProfessorReviewSchema
    diagram_evaluation: Optional[DiagramEvaluationSchema] = None
    answer_script_id: Optional[int] = None
    answer_script_file_name: Optional[str] = None
    answer_script_page_count: Optional[int] = None

