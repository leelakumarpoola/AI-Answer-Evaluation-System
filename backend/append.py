content = '''
@router.post("/answer-scripts/{answer_script_id}/feedback")
def generate_ai_feedback(answer_script_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    try:
        script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
        if not script:
            raise HTTPException(status_code=404, detail="Answer script not found")
        exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
        if not exam or exam.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to generate feedback for this script")
        
        from app.services.feedback_service import generate_and_store_feedback
        from app.schemas.feedback import FeedbackResponse
        
        student_answers = db.query(models.StudentAnswer).filter(models.StudentAnswer.answer_script_id == script.id).all()
        if not student_answers:
            raise HTTPException(status_code=404, detail="No student answers found for this script")
            
        feedback_results = []
        for answer in student_answers:
            if answer.evaluation:
                feedback = generate_and_store_feedback(db, answer.evaluation)
                feedback_results.append(FeedbackResponse.model_validate(feedback))
                
        return {"answer_script_id": answer_script_id, "status": "completed", "feedback": feedback_results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/answer-scripts/{answer_script_id}/feedback")
def get_ai_feedback(answer_script_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    try:
        script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
        if not script:
            raise HTTPException(status_code=404, detail="Answer script not found")
            
        if current_user.role == "student":
            if script.student_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to view feedback for other students' scripts")
        else:
            exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
            if not exam or exam.professor_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to view feedback for this script")
                
        from app.schemas.feedback import FeedbackResponse
        student_answers = db.query(models.StudentAnswer).filter(models.StudentAnswer.answer_script_id == script.id).all()
        
        feedback_results = []
        for answer in student_answers:
            if answer.evaluation and answer.evaluation.feedback:
                for fb in answer.evaluation.feedback:
                    feedback_results.append(FeedbackResponse.model_validate(fb))
                    
        return {"answer_script_id": answer_script_id, "status": "completed", "feedback": feedback_results}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
'''

with open('app/routers/answer_scripts.py', 'a') as f:
    f.write(content)
