from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List
import os
import shutil
import uuid

from app import models
from app.schemas.document import ExamDocumentResponse
from app.database import get_db
from app.utils.dependencies import require_professor
from app.schemas.auth import CurrentUser

router = APIRouter(
    prefix="/exams/{exam_id}/documents",
    tags=["Exam Documents"]
)

ALLOWED_DOC_TYPES = ["question_paper", "model_answer", "marks_rubric"]
MAX_FILE_SIZE = 20 * 1024 * 1024 # 20 MB

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@router.post("/", response_model=ExamDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    exam_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    if document_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid document_type. Allowed: {ALLOWED_DOC_TYPES}")
        
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check exam ownership
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    # Read file to get size and check for empty
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size == 0:
        raise HTTPException(status_code=400, detail="File is empty")
        
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File size exceeds 20MB limit")
        
    # Prepare storage path
    exam_dir = os.path.join(UPLOAD_DIR, "exams", str(exam_id), document_type)
    os.makedirs(exam_dir, exist_ok=True)
    
    # Check for existing document of this type
    existing_doc = db.query(models.ExamDocument).filter(
        models.ExamDocument.exam_id == exam_id,
        models.ExamDocument.document_type == document_type
    ).first()
    
    # Save the physical file safely using UUID
    safe_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(exam_dir, safe_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
        
    if existing_doc:
        # Delete old file
        if os.path.exists(existing_doc.file_path):
            try:
                os.remove(existing_doc.file_path)
            except Exception:
                pass
                
        # Update metadata
        existing_doc.file_name = file.filename
        existing_doc.file_path = file_path
        existing_doc.file_type = file.content_type
        existing_doc.file_size = file_size
        existing_doc.upload_status = "uploaded"
        doc = existing_doc
    else:
        doc = models.ExamDocument(
            exam_id=exam_id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_type=file.content_type,
            file_size=file_size,
            upload_status="uploaded"
        )
        db.add(doc)
        
    try:
        db.commit()
        db.refresh(doc)
        return doc
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Database integrity error")

@router.get("/", response_model=List[ExamDocumentResponse])
def get_documents(
    exam_id: int, 
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    documents = db.query(models.ExamDocument).filter(models.ExamDocument.exam_id == exam_id).all()
    return documents

@router.get("/{document_id}", response_model=ExamDocumentResponse)
def get_document(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return document

@router.get("/{document_id}/download")
def download_document(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Physical file not found on server")
        
    return FileResponse(
        path=document.file_path, 
        filename=document.file_name, 
        media_type=document.file_type
    )

from app.services.document_processing_service import process_document
from app.schemas.document import ProcessedPageResponse

@router.post("/{document_id}/process", response_model=ExamDocumentResponse)
def process_exam_document(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.file_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDFs can be processed")
        
    return process_document(document.id, db)

@router.get("/{document_id}/pages", response_model=List[ProcessedPageResponse])
def get_processed_pages(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    output_dir = os.path.join("uploads", "processed", "exams", str(exam_id), str(document_id))
    
    if not os.path.exists(output_dir):
        return []
        
    pages = []
    for file_name in sorted(os.listdir(output_dir)):
        if file_name.endswith(".png") and file_name.startswith("page_"):
            # extract page number e.g. page_001.png
            try:
                page_num = int(file_name.split("_")[1].split(".")[0])
                pages.append({"page_number": page_num, "file_name": file_name})
            except Exception:
                pass
                
    return pages

from app.services.ocr_service import process_document_ocr
from app.schemas.ocr import OCRDocumentResponse
from app.models.ocr_result import OCRResult

@router.post("/{document_id}/ocr", response_model=OCRDocumentResponse)
def run_ocr(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    return process_document_ocr(document_id, db)

@router.get("/{document_id}/ocr", response_model=OCRDocumentResponse)
def get_ocr_results(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    results = db.query(OCRResult).filter(OCRResult.document_id == document_id).order_by(OCRResult.page_number).all()
    
    status = "processed" if results else "pending"
    if any(r.ocr_status == "failed" for r in results):
        status = "partial_failure"
        
    return {
        "document_id": document_id,
        "status": status,
        "pages": [
            {
                "page_number": r.page_number,
                "text": r.extracted_text,
                "ocr_status": r.ocr_status,
                "ocr_confidence": r.ocr_confidence
            }
            for r in results
        ]
    }

from app.services.document_extraction_service import extract_information
from app.models.question import Question
from app.models.model_answer import ModelAnswer
from app.models.rubric import Rubric

@router.post("/{document_id}/extract")
def run_extraction(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    return extract_information(exam_id, document_id, db)

@router.get("/{document_id}/extraction")
def get_extraction_results(
    exam_id: int, 
    document_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_professor)
):
    exam = db.query(models.Exam).filter(models.Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
        
    if exam.professor_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not own this exam")
        
    document = db.query(models.ExamDocument).filter(
        models.ExamDocument.id == document_id,
        models.ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc_type = document.document_type
    
    if doc_type == "question_paper":
        qs = db.query(Question).filter(Question.exam_id == exam_id).all()
        return {
            "document_type": doc_type,
            "questions": [{"question_number": q.question_number, "question_text": q.question_text, "max_marks": q.max_marks} for q in qs]
        }
    elif doc_type == "model_answer":
        qs = db.query(Question).filter(Question.exam_id == exam_id).all()
        answers = []
        for q in qs:
            ans = db.query(ModelAnswer).filter(ModelAnswer.question_id == q.id).first()
            if ans:
                answers.append({"question_number": q.question_number, "answer_text": ans.answer_text})
        return {
            "document_type": doc_type,
            "model_answers": answers
        }
    elif doc_type == "marks_rubric":
        qs = db.query(Question).filter(Question.exam_id == exam_id).all()
        rubrics_out = []
        for q in qs:
            rubs = db.query(Rubric).filter(Rubric.question_id == q.id).all()
            if rubs:
                rubrics_out.append({
                    "question_number": q.question_number,
                    "rubrics": [{"criterion": r.criterion, "marks": r.marks} for r in rubs]
                })
        return {
            "document_type": doc_type,
            "rubrics": rubrics_out
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported document type")

