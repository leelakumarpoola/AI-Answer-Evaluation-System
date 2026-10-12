from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app.utils.dependencies import require_professor
from app.schemas.auth import CurrentUser
from app.schemas.report import (
    ExamSummaryResponse,
    StudentPerformanceResponse,
    QuestionPerformanceResponse,
    MarksDistributionResponse,
    CompletionReportResponse
)
from app.services import report_service

router = APIRouter(tags=["reports"])

def _verify_exam_ownership(exam_id: int, current_user: CurrentUser, db: Session):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
    return exam

@router.get("/exams/{exam_id}/reports/summary", response_model=ExamSummaryResponse)
def get_exam_summary_report(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    _verify_exam_ownership(exam_id, current_user, db)
    data = report_service.generate_exam_summary(db, exam_id)
    if not data:
        raise HTTPException(status_code=404, detail="Summary could not be generated")
    return ExamSummaryResponse(**data)

@router.get("/exams/{exam_id}/reports/students", response_model=List[StudentPerformanceResponse])
def get_student_performance_report(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    _verify_exam_ownership(exam_id, current_user, db)
    data = report_service.get_student_performance(db, exam_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Data could not be generated")
    return data

@router.get("/exams/{exam_id}/reports/questions", response_model=List[QuestionPerformanceResponse])
def get_question_performance_report(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    _verify_exam_ownership(exam_id, current_user, db)
    data = report_service.get_question_performance(db, exam_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Data could not be generated")
    return data

@router.get("/exams/{exam_id}/reports/distribution", response_model=MarksDistributionResponse)
def get_marks_distribution_report(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    _verify_exam_ownership(exam_id, current_user, db)
    data = report_service.get_marks_distribution(db, exam_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Data could not be generated")
    return MarksDistributionResponse(**data)

@router.get("/exams/{exam_id}/reports/completion", response_model=CompletionReportResponse)
def get_completion_report(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    _verify_exam_ownership(exam_id, current_user, db)
    data = report_service.get_completion_report(db, exam_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Data could not be generated")
    return CompletionReportResponse(**data)
