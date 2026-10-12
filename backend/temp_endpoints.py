
@router.post("/{answer_script_id}/rubric-evaluation")
def evaluate_rubric_for_script(answer_script_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    try:
        script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
        if not script:
            raise HTTPException(status_code=404, detail="Answer script not found")
        exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
        if not exam or exam.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to evaluate this script")
        
        from app.services.rubric_evaluation_service import evaluate_rubric
        results = evaluate_rubric(answer_script_id, db)
        return {"answer_script_id": answer_script_id, "status": "completed", "results": results}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{answer_script_id}/rubric-evaluation")
def get_rubric_evaluation_for_script(answer_script_id: int, db: Session = Depends(get_db), current_user: CurrentUser = Depends(require_professor)):
    try:
        script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
        if not script:
            raise HTTPException(status_code=404, detail="Answer script not found")
        exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
        if not exam or exam.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this script's evaluation")
        
        from app.services.rubric_evaluation_service import get_rubric_evaluation
        results = get_rubric_evaluation(answer_script_id, db)
        return {"answer_script_id": answer_script_id, "status": "completed", "results": results}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
