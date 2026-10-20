from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models
from app.utils.dependencies import require_professor
from app.schemas.auth import CurrentUser

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    # Get total subjects, exams, students
    # Subjects and students aren't strictly tied to professor but we just count all for now
    total_subjects = db.query(models.Subject).filter(models.Subject.professor_id == current_user.id).count()
    total_exams = db.query(models.Exam).filter(models.Exam.professor_id == current_user.id).count()
    total_students = db.query(models.Student).count()
    
    # For evaluations, we need to join AnswerScript -> Exam
    # Or just count evaluations on answer scripts that belong to this professor's exams
    evaluations = db.query(models.Evaluation).join(
        models.StudentAnswer
    ).join(
        models.AnswerScript
    ).join(
        models.Exam
    ).filter(
        models.Exam.professor_id == current_user.id
    ).all()
    
    pending = 0
    completed = 0
    approved = 0
    
    for ev in evaluations:
        if ev.review_status == "approved":
            approved += 1
        elif ev.review_status == "reviewed":
            completed += 1
        elif ev.evaluation_status == "completed":
            completed += 1
        else:
            pending += 1
            
    return {
        "subjects": total_subjects,
        "exams": total_exams,
        "students": total_students,
        "pending": pending,
        "completed": completed,
        "approved": approved
    }
