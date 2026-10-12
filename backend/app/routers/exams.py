from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app import models
from app.schemas.exam import ExamCreate, ExamResponse
from app.database import get_db
from app.utils.dependencies import require_professor, get_current_user
from app.schemas.auth import CurrentUser

router = APIRouter(
    prefix="/exams",
    tags=["Exams"]
)

@router.get("/", response_model=List[ExamResponse])
def get_exams(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    return db.query(models.Exam).filter(models.Exam.professor_id == current_user.id).all()

@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if current_user.role == "professor" and exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this exam")
    return exam

@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(exam_in: ExamCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    subject = db.query(models.Subject).filter(models.Subject.id == exam_in.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    exam_data = exam_in.model_dump()
    new_exam = models.Exam(**exam_data, professor_id=current_user.id)
    db.add(new_exam)
    try:
        db.commit()
        db.refresh(new_exam)
        return new_exam
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")
