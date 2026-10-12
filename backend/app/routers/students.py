from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from app import models
from app.schemas.student import StudentCreate, StudentResponse
from app.database import get_db
from app.utils.dependencies import require_professor, get_current_user
from app.schemas.auth import CurrentUser

router = APIRouter(
    prefix="/students",
    tags=["Students"]
)

@router.get("/", response_model=List[StudentResponse])
def get_students(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    students = db.query(models.Student).all()
    return students

@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    if current_user.role == "student" and current_user.id != student_id:
        raise HTTPException(status_code=403, detail="Not authorized to access other student profiles")
        
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.post("/", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_in: StudentCreate, db: Session = Depends(get_db)):
    # Check for duplicate roll_number or email before insert to provide specific error
    existing_roll = db.query(models.Student).filter(models.Student.roll_number == student_in.roll_number).first()
    if existing_roll:
        raise HTTPException(status_code=400, detail="Student with this registration number already exists")
        
    existing_email = db.query(models.Student).filter(models.Student.email == student_in.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Student with this email already exists")

    new_student = models.Student(**student_in.model_dump())
    db.add(new_student)
    try:
        db.commit()
        db.refresh(new_student)
        return new_student
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error. Duplicate data.")
