import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.dependencies import require_professor, get_current_user
from app.schemas.auth import CurrentUser
from app.services.document_processing_service import process_answer_script
from app.services.ocr_service import process_answer_script_ocr, get_answer_script_ocr_results
from app.schemas.answer_script import AnswerScriptResponse, AnswerScriptOCRResponse

router = APIRouter(
    tags=["Answer Scripts"]
)

UPLOAD_DIR = os.path.join("uploads", "answer_scripts", "exams")

@router.post("/exams/{exam_id}/students/{student_id}/answer-script", response_model=AnswerScriptResponse)
def upload_answer_script(
    exam_id: int,
    student_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
        
    # Check for existing script and remove
    existing_script = db.query(models.AnswerScript).filter(
        models.AnswerScript.exam_id == exam_id,
        models.AnswerScript.student_id == student_id
    ).first()
    
    if existing_script:
        if existing_script.file_path and os.path.exists(existing_script.file_path):
            os.remove(existing_script.file_path)
        db.delete(existing_script)
        db.commit()
        
    # Save file
    file_dir = os.path.join(UPLOAD_DIR, str(exam_id), "students", str(student_id))
    os.makedirs(file_dir, exist_ok=True)
    
    file_path = os.path.join(file_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
    new_script = models.AnswerScript(
        exam_id=exam_id,
        student_id=student_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file.content_type,
        file_size=file_size,
        upload_status="uploaded"
    )
    db.add(new_script)
    db.commit()
    db.refresh(new_script)
    return new_script

@router.post("/answer-scripts/{answer_script_id}/process")
def process_script(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    return process_answer_script(answer_script_id, db)

@router.post("/answer-scripts/{answer_script_id}/ocr")
def run_ocr(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: models.Professor = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    process_answer_script_ocr(answer_script_id, db)
    return {"status": "processed", "message": "OCR completed successfully"}

@router.get("/answer-scripts/{answer_script_id}/ocr", response_model=AnswerScriptOCRResponse)
def get_ocr_results(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: models.Professor = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    return get_answer_script_ocr_results(answer_script_id, db)

from app.services.student_answer_extraction_service import extract_student_answers, get_student_answers

@router.post("/answer-scripts/{answer_script_id}/extract-answers")
def run_extract_student_answers(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    return extract_student_answers(answer_script_id, db)

@router.get("/answer-scripts/{answer_script_id}/answers")
def fetch_student_answers(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    return get_student_answers(answer_script_id, db)

from app.services.semantic_similarity_service import calculate_semantic_similarity, get_similarity_results

@router.post("/answer-scripts/{answer_script_id}/semantic-similarity")
def run_semantic_similarity(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    return calculate_semantic_similarity(answer_script_id, db)

@router.get("/answer-scripts/{answer_script_id}/semantic-similarity")
def fetch_semantic_similarity(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
        
    return get_similarity_results(answer_script_id, db)

@router.post("/answer-scripts/{answer_script_id}/rubric-evaluation")
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/answer-scripts/{answer_script_id}/rubric-evaluation")
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
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
