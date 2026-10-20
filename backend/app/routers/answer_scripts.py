import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.utils.dependencies import require_professor, get_current_user, get_current_user_flexible
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


def _serve_answer_script_pdf(script: models.AnswerScript):
    """
    Validates and streams the complete original scanned answer-sheet PDF file.
    Preserves original handwriting, image resolution, and page order without modification.
    """
    if not script.file_path or not os.path.exists(script.file_path):
        raise HTTPException(
            status_code=404,
            detail="Original student answer sheet PDF file was not found on server."
        )

    file_name = script.file_name or f"student_answer_script_{script.id}.pdf"
    
    # Return raw PDF with inline disposition to open in browser native PDF viewer
    return FileResponse(
        path=script.file_path,
        media_type="application/pdf",
        filename=file_name,
        headers={
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Content-Type": "application/pdf"
        }
    )


@router.get("/answer-scripts/{answer_script_id}/pdf")
def get_answer_script_pdf(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_flexible)
):
    """
    Returns the complete, original scanned answer sheet PDF for an answer script.
    Authorized for the professor owning the exam or the student who submitted the script.
    """
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script record not found")

    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Associated exam not found")

    if current_user.role == "professor":
        if exam.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")
    elif current_user.role == "student":
        if script.student_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to view other students' answer scripts")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    return _serve_answer_script_pdf(script)


@router.get("/exams/{exam_id}/students/{student_id}/answer-script/pdf")
def get_exam_student_answer_script_pdf(
    exam_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_flexible)
):
    """
    Returns the complete, original scanned answer sheet PDF for a student and exam.
    Authorized for the exam professor or the student.
    """
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role == "professor":
        if exam.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own this exam")
    elif current_user.role == "student":
        if student_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to view this answer script")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    script = db.query(models.AnswerScript).filter(
        models.AnswerScript.exam_id == exam_id,
        models.AnswerScript.student_id == student_id
    ).first()

    if not script:
        raise HTTPException(status_code=404, detail="No answer script uploaded for this student in this exam")

    return _serve_answer_script_pdf(script)


@router.get("/evaluations/{evaluation_id}/answer-script/pdf")
def get_evaluation_answer_script_pdf(
    evaluation_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user_flexible)
):
    """
    Returns the original answer sheet PDF directly from an evaluation ID.
    """
    eval_record = db.query(models.Evaluation).filter(models.Evaluation.id == evaluation_id).first()
    if not eval_record:
        raise HTTPException(status_code=404, detail="Evaluation record not found")

    student_answer = eval_record.student_answer
    if not student_answer:
        raise HTTPException(status_code=404, detail="Student answer not found for evaluation")

    script = student_answer.answer_script
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")

    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    if current_user.role == "professor":
        if exam.professor_id != current_user.id:
            raise HTTPException(status_code=403, detail="You do not own the exam for this evaluation")
    elif current_user.role == "student":
        if script.student_id != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to view this answer script")
    else:
        raise HTTPException(status_code=403, detail="Unauthorized role")

    return _serve_answer_script_pdf(script)


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


@router.post("/answer-scripts/{answer_script_id}/evaluate-full")
def evaluate_full_pipeline(
    answer_script_id: int, 
    db: Session = Depends(get_db), 
    current_user: CurrentUser = Depends(require_professor)
):
    """
    Executes the complete end-to-end evaluation pipeline:
    1. PDF → images (if not done)
    2. OCR (if not done)
    3. Answer segmentation
    4. Semantic similarity
    5. Rubric evaluation
    6. Feedback generation
    
    Returns detailed results including answers flagged for review.
    """
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if not exam or exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own the exam for this answer script")

    # Pre-check: question paper must have been processed first
    from app.models.question import Question
    questions = db.query(Question).filter(Question.exam_id == script.exam_id).all()
    if not questions:
        # Auto-process master documents if they exist and are not yet extracted
        from app.models.exam_document import ExamDocument
        from app.services.document_processing_service import process_document
        from app.services.ocr_service import process_document_ocr
        from app.services.document_extraction_service import extract_information

        qp_doc = db.query(ExamDocument).filter(
            ExamDocument.exam_id == script.exam_id,
            ExamDocument.document_type == "question_paper"
        ).first()

        if qp_doc:
            logger.info(f"Auto-processing question paper for exam {script.exam_id}...")
            try:
                if qp_doc.processing_status != "processed":
                    process_document(qp_doc.id, db)
                process_document_ocr(qp_doc.id, db)
                extract_information(script.exam_id, qp_doc.id, db)

                for dtype in ["model_answer", "marks_rubric"]:
                    m_doc = db.query(ExamDocument).filter(
                        ExamDocument.exam_id == script.exam_id,
                        ExamDocument.document_type == dtype
                    ).first()
                    if m_doc:
                        if m_doc.processing_status != "processed":
                            process_document(m_doc.id, db)
                        process_document_ocr(m_doc.id, db)
                        extract_information(script.exam_id, m_doc.id, db)

                questions = db.query(Question).filter(Question.exam_id == script.exam_id).all()
            except Exception as auto_err:
                logger.error(f"Auto-processing master documents error: {auto_err}")

    if not questions:
        raise HTTPException(
            status_code=400,
            detail=(
                "No questions found for this exam. "
                "Please upload the question paper and click 'Process Documents' first."
            )
        )
        
    from app.services.student_answer_extraction_service import extract_student_answers
    from app.services.semantic_similarity_service import calculate_semantic_similarity
    from app.services.rubric_evaluation_service import evaluate_rubric
    from app.services.feedback_service import generate_and_store_feedback

    pipeline_status = {}

    # 1. Page rendering
    if script.processing_status != "processed":
        process_answer_script(answer_script_id, db)
        pipeline_status["rendering"] = "completed"
    else:
        pipeline_status["rendering"] = "cached"
        
    # 2. OCR
    if script.ocr_status != "processed":
        process_answer_script_ocr(answer_script_id, db)
        pipeline_status["ocr"] = "completed"
    else:
        pipeline_status["ocr"] = "cached"
        
    # 3. Answer Segmentation
    extraction_result = extract_student_answers(answer_script_id, db)
    pipeline_status["segmentation"] = extraction_result.get("extraction_method", "completed")
    
    # 4. Semantic Similarity
    calculate_semantic_similarity(answer_script_id, db)
    pipeline_status["similarity"] = "completed"
    
    # 5. Rubric Evaluation
    rubric_results = evaluate_rubric(answer_script_id, db)
    pipeline_status["rubric_evaluation"] = "completed"
    
    # 6. Feedback Generation
    student_answers = db.query(models.StudentAnswer).filter(
        models.StudentAnswer.answer_script_id == script.id
    ).all()
    feedback_results = []
    for sa in student_answers:
        if sa.evaluation:
            fb = generate_and_store_feedback(db, sa.evaluation)
            feedback_results.append({
                "evaluation_id": sa.evaluation.id,
                "feedback": fb.feedback_text
            })

    # Collect review flags
    needs_review = [
        r for r in rubric_results
        if r.get("needs_review") or r.get("status") in ("rubric_missing", "model_answer_missing")
    ]

    return {
        "answer_script_id": answer_script_id,
        "status": "completed",
        "pipeline_status": pipeline_status,
        "evaluations_count": len(rubric_results),
        "feedback_count": len(feedback_results),
        "needs_review_count": len(needs_review),
        "total_words_ocr": extraction_result.get("total_words", 0),
        "extraction_method": extraction_result.get("extraction_method", "unknown"),
        "message": (
            f"Evaluation complete. {len(needs_review)} answer(s) flagged for manual review."
            if needs_review else "Evaluation complete. All answers evaluated with confidence."
        )
    }


@router.get("/answer-scripts/{answer_script_id}/ocr/benchmark")
def benchmark_ocr_engines(
    answer_script_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    """
    Benchmark Tesseract vs TrOCR on the first 3 pages of an answer script.
    Requires the script to have been processed (PDF → images) first.
    
    TrOCR must be enabled via TROCR_ENABLED=true in .env.
    """
    script = db.query(models.AnswerScript).filter(models.AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
    
    exam = db.query(models.Exam).filter(models.Exam.id == script.exam_id).first()
    if not exam or exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if script.processing_status != "processed":
        raise HTTPException(
            status_code=400,
            detail="Process the answer script first (PDF → images) before benchmarking"
        )

    from app.services.document_processing_service import PROCESSED_ANSWERS_DIR
    from app.services.trocr_service import benchmark_ocr_backends
    import os

    image_dir = os.path.join(PROCESSED_ANSWERS_DIR, str(answer_script_id))
    if not os.path.exists(image_dir):
        raise HTTPException(status_code=400, detail="No processed images found")

    # Benchmark on first 3 pages max
    image_files = sorted([
        os.path.join(image_dir, f)
        for f in os.listdir(image_dir)
        if f.endswith(".png") and f.startswith("page_")
    ])[:3]

    if not image_files:
        raise HTTPException(status_code=400, detail="No page images available for benchmarking")

    result = benchmark_ocr_backends(image_files)
    return result

