from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app import models
from app.models.rubric_evaluation import RubricEvaluation
from app.utils.dependencies import require_professor
from app.schemas.auth import CurrentUser
from app.schemas.review import (
    ReviewUpdateRequest,
    FullReviewPackageResponse,
    StudentInfoSchema,
    ExamInfoSchema,
    QuestionInfoSchema,
    StudentAnswerInfoSchema,
    ModelAnswerInfoSchema,
    RubricInfoSchema,
    CriterionEvaluationSchema,
    AIEvaluationSchema,
    ProfessorReviewSchema
)

router = APIRouter(tags=["evaluations"])

def _get_evaluation_and_verify_ownership(evaluation_id: int, db: Session, current_user: CurrentUser):
    eval_record = db.query(models.Evaluation).filter(models.Evaluation.id == evaluation_id).first()
    if not eval_record:
        raise HTTPException(status_code=404, detail="Evaluation not found")
        
    student_answer = eval_record.student_answer
    if not student_answer:
        raise HTTPException(status_code=404, detail="Student answer not found")
        
    script = student_answer.answer_script
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this evaluation")
        
    return eval_record, student_answer, script, exam

@router.get("/evaluations/{evaluation_id}/review", response_model=FullReviewPackageResponse)
def get_evaluation_review(evaluation_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    eval_record, student_answer, script, exam = _get_evaluation_and_verify_ownership(evaluation_id, db, current_user)
    
    student = script.student
    subject = exam.subject
    question = student_answer.question
    
    student_info = StudentInfoSchema(
        name=student.name,
        roll_number=student.roll_number,
        department=student.department,
        year=student.year,
        section=student.section
    )
    
    exam_info = ExamInfoSchema(
        subject_name=subject.name,
        course_code=subject.code,
        exam_name=exam.name,
        exam_date=exam.exam_date
    )
    
    question_info = QuestionInfoSchema(
        question_number=question.question_number,
        question_text=question.question_text,
        max_marks=question.max_marks
    )
    
    student_answer_info = StudentAnswerInfoSchema(
        answer_text=student_answer.answer_text,
        page_range=f"{student_answer.start_page}-{student_answer.end_page}" if student_answer.start_page else None
    )
    
    model_answer_info = None
    if question.model_answer:
        model_answer_info = ModelAnswerInfoSchema(answer_text=question.model_answer.answer_text)
        
    rubrics_info = []
    for rubric in question.rubrics:
        rubrics_info.append(RubricInfoSchema(
            criterion=rubric.criterion,
            description=rubric.description,
            max_marks=rubric.marks
        ))
        
    crit_evals = []
    for crit in eval_record.criterion_evaluations:
        crit_evals.append(CriterionEvaluationSchema(
            criterion=crit.rubric.criterion,
            evidence_score=crit.evidence_score,
            suggested_marks=crit.suggested_marks,
            reason=crit.reason
        ))
        
    ai_feedback_text = None
    if eval_record.feedback and len(eval_record.feedback) > 0:
        ai_feedback_text = eval_record.feedback[-1].feedback_text
        
    ai_eval_info = AIEvaluationSchema(
        similarity_score=eval_record.similarity_score,
        criterion_evaluations=crit_evals,
        ai_suggested_marks=eval_record.awarded_marks,
        ai_feedback=ai_feedback_text
    )
    
    prof_review = ProfessorReviewSchema(
        final_marks=eval_record.final_marks,
        professor_remarks=eval_record.professor_remarks,
        review_status=eval_record.review_status or "ai_evaluated",
        reviewed_at=eval_record.reviewed_at,
        approved_at=eval_record.approved_at
    )
    
    return FullReviewPackageResponse(
        evaluation_id=eval_record.id,
        student_info=student_info,
        exam_info=exam_info,
        question_info=question_info,
        student_answer_info=student_answer_info,
        model_answer_info=model_answer_info,
        rubrics=rubrics_info,
        ai_evaluation=ai_eval_info,
        professor_review=prof_review
    )

@router.patch("/evaluations/{evaluation_id}/review")
def update_evaluation_review(evaluation_id: int, update_data: ReviewUpdateRequest, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    eval_record, student_answer, script, exam = _get_evaluation_and_verify_ownership(evaluation_id, db, current_user)
    
    if eval_record.review_status == "approved":
        raise HTTPException(status_code=409, detail="Evaluation has already been approved and is locked.")
        
    max_marks = student_answer.question.max_marks
    if not (0 <= update_data.final_marks <= max_marks):
        raise HTTPException(status_code=400, detail=f"Final marks must be between 0 and {max_marks}")
        
    eval_record.final_marks = update_data.final_marks
    if update_data.professor_remarks is not None:
        eval_record.professor_remarks = update_data.professor_remarks
        
    eval_record.review_status = "under_review"
    eval_record.reviewed_by = current_user.id
    import datetime as dt
    eval_record.reviewed_at = dt.datetime.now(dt.timezone.utc)
    
    db.commit()
    db.refresh(eval_record)
    return {"message": "Review updated successfully", "final_marks": eval_record.final_marks, "review_status": eval_record.review_status}

@router.post("/evaluations/{evaluation_id}/approve")
def approve_evaluation(evaluation_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    eval_record, student_answer, script, exam = _get_evaluation_and_verify_ownership(evaluation_id, db, current_user)
    
    if eval_record.final_marks is None:
        raise HTTPException(status_code=400, detail="Cannot approve without final marks. Please submit review marks first.")
        
    eval_record.review_status = "approved"
    eval_record.reviewed_by = current_user.id
    import datetime as dt
    eval_record.approved_at = dt.datetime.now(dt.timezone.utc)
    
    db.commit()
    db.refresh(eval_record)
    return {"message": "Evaluation approved successfully", "review_status": eval_record.review_status}

@router.get("/exams/{exam_id}/evaluations")
def get_exam_evaluations(exam_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    # Get all answer scripts for this exam
    scripts = db.query(models.AnswerScript).filter(models.AnswerScript.exam_id == exam_id).all()
    script_ids = [s.id for s in scripts]
    
    # Get all student answers
    answers = db.query(models.StudentAnswer).filter(models.StudentAnswer.answer_script_id.in_(script_ids)).all()
    answer_ids = [a.id for a in answers]
    
    # Get all evaluations
    evals = db.query(models.Evaluation).filter(models.Evaluation.student_answer_id.in_(answer_ids)).all()
    
    results = []
    for ev in evals:
        student = ev.student_answer.answer_script.student
        question = ev.student_answer.question
        results.append({
            "evaluation_id": ev.id,
            "student_roll_number": student.roll_number,
            "student_name": student.name,
            "question_number": question.question_number,
            "max_marks": question.max_marks,
            "ai_suggested_marks": ev.awarded_marks,
            "final_marks": ev.final_marks,
            "review_status": ev.review_status
        })
        
    return {"exam_id": exam_id, "evaluations": results}
