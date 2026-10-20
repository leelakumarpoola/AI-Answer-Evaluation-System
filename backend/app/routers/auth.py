from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.schemas.auth import ProfessorRegister, ProfessorLogin, StudentRegister, StudentLogin, Token, CurrentUser
from app.models.professor import Professor
from app.models.student import Student
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.utils.dependencies import get_current_user, require_professor, require_student

import re

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

def validate_password_rules(password: str) -> None:
    """
    Validates that password satisfies minimum security guidelines:
    - At least 8 characters long
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one numeric digit (0-9)
    - At least one special symbol (@$!%*?&#^_-.+=~)
    """
    if len(password) < 8:
        raise HTTPException(
            status_code=400, 
            detail="Password must be at least 8 characters long"
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=400, 
            detail="Password must contain at least one uppercase letter (A-Z)"
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=400, 
            detail="Password must contain at least one lowercase letter (a-z)"
        )
    if not re.search(r"[0-9]", password):
        raise HTTPException(
            status_code=400, 
            detail="Password must contain at least one numeric digit (0-9)"
        )
    if not re.search(r"[@$!%*?&#^_\-\.+=\~]", password):
        raise HTTPException(
            status_code=400, 
            detail="Password must contain at least one special symbol (e.g. @$!%*?&#^_-.+=~)"
        )

@router.post("/professor/register", response_model=CurrentUser, status_code=status.HTTP_201_CREATED)
def register_professor(prof_in: ProfessorRegister, db: Session = Depends(get_db)):
    # Enforce password complexity rules
    validate_password_rules(prof_in.password)
        
    existing_prof = db.query(Professor).filter(Professor.email == prof_in.email).first()
    if existing_prof:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pw = get_password_hash(prof_in.password)
    
    new_prof = Professor(
        name=prof_in.name,
        email=prof_in.email,
        department=prof_in.department,
        password_hash=hashed_pw
    )
    
    db.add(new_prof)
    try:
        db.commit()
        db.refresh(new_prof)
        return CurrentUser(id=new_prof.id, email=new_prof.email, role="professor", name=new_prof.name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database error during registration")

@router.post("/professor/login", response_model=Token)
def login_professor(prof_in: ProfessorLogin, db: Session = Depends(get_db)):
    prof = db.query(Professor).filter(Professor.email == prof_in.email).first()
    if not prof or not prof.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not verify_password(prof_in.password, prof.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not prof.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
        
    access_token = create_access_token(data={"sub": str(prof.id), "role": "professor"})
    
    return Token(access_token=access_token, role="professor")

@router.post("/student/register", response_model=CurrentUser)
def register_student(student_in: StudentRegister, db: Session = Depends(get_db)):
    validate_password_rules(student_in.password)
        
    student = db.query(Student).filter(
        Student.roll_number == student_in.roll_number,
        Student.email == student_in.email
    ).first()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found with provided registration number and email")
        
    if student.password_hash:
        raise HTTPException(status_code=400, detail="Account already has authentication credentials set up")
        
    student.password_hash = get_password_hash(student_in.password)
    db.commit()
    db.refresh(student)
    
    return CurrentUser(id=student.id, email=student.email, role="student", name=student.name)

@router.post("/student/login", response_model=Token)
def login_student(student_in: StudentLogin, db: Session = Depends(get_db)):
    student = db.query(Student).filter(
        (Student.email == student_in.identifier) | (Student.roll_number == student_in.identifier)
    ).first()
    
    if not student or not student.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not verify_password(student_in.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not student.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")
        
    access_token = create_access_token(data={"sub": str(student.id), "role": "student"})
    
    return Token(access_token=access_token, role="student")

@router.get("/me", response_model=CurrentUser)
def get_me(current_user: CurrentUser = Depends(get_current_user)):
    return current_user

@router.get("/professor-test", response_model=dict)
def professor_test(current_user: CurrentUser = Depends(require_professor)):
    return {"message": "You have access to professor-only endpoints", "user": current_user.email}

@router.get("/student-test", response_model=dict)
def student_test(current_user: CurrentUser = Depends(require_student)):
    return {"message": "You have access to student-only endpoints", "user": current_user.email}

