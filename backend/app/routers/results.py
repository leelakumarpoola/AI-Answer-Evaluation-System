from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models
from app.utils.dependencies import require_professor, require_student
from app.schemas.auth import CurrentUser
from app.schemas.result import ExamResultSchema, StudentResultSummarySchema
from app.services.result_service import generate_student_exam_result

router = APIRouter(tags=["results"])

@router.get("/exams/{exam_id}/results", response_model=List[StudentResultSummarySchema])
def get_exam_results_summary(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    scripts = db.query(models.AnswerScript).filter(models.AnswerScript.exam_id == exam_id).all()
    student_ids = [s.student_id for s in scripts]
    
    results = []
    for script in scripts:
        res = generate_student_exam_result(db, exam_id, script.student_id)
        if res:
            results.append(StudentResultSummarySchema(
                student_id=script.student_id,
                answer_script_id=script.id,
                student_name=res["student_name"],
                roll_number=res["roll_number"],
                total_marks=res["total_marks"],
                maximum_marks=res["maximum_marks"],
                percentage=res["percentage"],
                status=res["status"]
            ))
            
    return results

@router.get("/exams/{exam_id}/students/{student_id}/result", response_model=ExamResultSchema)
def get_student_result_for_professor(exam_id: int, student_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    res = generate_student_exam_result(db, exam_id, student_id)
    if not res:
        raise HTTPException(status_code=404, detail="Result could not be generated")
        
    return ExamResultSchema(**res)

@router.get("/students/me/results", response_model=List[ExamResultSchema])
def get_my_results(db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_student)):
    scripts = db.query(models.AnswerScript).filter(models.AnswerScript.student_id == current_user.id).all()
    exam_ids = list(set([s.exam_id for s in scripts]))
    
    results = []
    for eid in exam_ids:
        res = generate_student_exam_result(db, eid, current_user.id)
        if res:
            results.append(ExamResultSchema(**res))
            
    return results

@router.get("/my-results/{exam_id}", response_model=ExamResultSchema)
def get_my_result_for_exam(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_student)):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.exam_id == exam_id, models.AnswerScript.student_id == current_user.id).first()
    if not script:
        raise HTTPException(status_code=404, detail="You have no answer script for this exam")
        
    res = generate_student_exam_result(db, exam_id, current_user.id)
    if not res:
        raise HTTPException(status_code=404, detail="Result could not be generated")
        
    return ExamResultSchema(**res)
