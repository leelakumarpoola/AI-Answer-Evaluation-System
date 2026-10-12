from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app import models
from app.schemas.subject import SubjectCreate, SubjectResponse
from app.database import get_db
from app.utils.dependencies import require_professor, get_current_user
from app.schemas.auth import CurrentUser

router = APIRouter(
    prefix="/subjects",
    tags=["Subjects"]
)

@router.get("/", response_model=List[SubjectResponse])
def get_subjects(db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    return db.query(models.Subject).all()

@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(subject_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.post("/", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(subject_in: SubjectCreate, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    existing = db.query(models.Subject).filter(models.Subject.code == subject_in.code).first()
    if existing:
        raise HTTPException(status_code=409, detail="Subject with this code already exists")
        
    new_subject = models.Subject(**subject_in.model_dump())
    db.add(new_subject)
    try:
        db.commit()
        db.refresh(new_subject)
        return new_subject
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")

# Additional endpoint to get exams for a subject
from app.schemas.exam import ExamResponse
@router.get("/{subject_id}/exams", response_model=List[ExamResponse])
def get_exams_for_subject(subject_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    query = db.query(models.Exam).filter(models.Exam.subject_id == subject_id)
    if current_user.role == "professor":
        query = query.filter(models.Exam.professor_id == current_user.id)
    return query.all()

