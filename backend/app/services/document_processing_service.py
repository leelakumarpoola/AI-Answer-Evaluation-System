import os
import shutil
import fitz  # PyMuPDF
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
from app.models.exam_document import ExamDocument

PROCESSED_DIR = os.path.join("uploads", "processed", "exams")

def process_document(document_id: int, db: Session):
    # Fetch document
    document = db.query(ExamDocument).filter(ExamDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    exam_id = document.exam_id
    
    # Update status to processing
    document.processing_status = "processing"
    document.processing_error = None
    db.commit()
    
    # Paths
    doc_path = document.file_path
    if not os.path.exists(doc_path):
        document.processing_status = "failed"
        document.processing_error = "Physical PDF file not found"
        db.commit()
        raise HTTPException(status_code=404, detail="Physical PDF file not found")
        
    output_dir = os.path.join(PROCESSED_DIR, str(exam_id), str(document_id))
    
    # Clear directory for idempotency
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Open PDF
        try:
            pdf_document = fitz.open(doc_path)
        except Exception as e:
            raise Exception(f"Failed to open PDF: {str(e)}")
            
        page_count = len(pdf_document)
        if page_count == 0:
            raise Exception("PDF contains zero pages")
            
        document.page_count = page_count
        
        # Process each page
        processed_count = 0
        for i in range(page_count):
            page = pdf_document.load_page(i)
            # Render page to an image at 300 DPI — required for handwritten document OCR accuracy
            pix = page.get_pixmap(dpi=300)
            
            # Save image
            page_filename = f"page_{i+1:03d}.png"
            page_filepath = os.path.join(output_dir, page_filename)
            pix.save(page_filepath)
            
            processed_count += 1
            
        pdf_document.close()
        
        # Update metadata
        document.processed_page_count = processed_count
        document.processing_status = "processed"
        document.processed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(document)
        return document
        
    except Exception as e:
        document.processing_status = "failed"
        document.processing_error = str(e)
        db.commit()
        db.refresh(document)
        raise HTTPException(status_code=400, detail=f"Processing failed: {str(e)}")

from app.models.answer_script import AnswerScript

PROCESSED_ANSWERS_DIR = os.path.join("uploads", "processed", "answer_scripts")

def process_answer_script(answer_script_id: int, db: Session):
    # Fetch document
    document = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    # Update status to processing
    document.processing_status = "processing"
    document.processing_error = None
    db.commit()
    
    # Paths
    doc_path = document.file_path
    if not os.path.exists(doc_path):
        document.processing_status = "failed"
        document.processing_error = "Physical PDF file not found"
        db.commit()
        raise HTTPException(status_code=404, detail="Physical PDF file not found")
        
    output_dir = os.path.join(PROCESSED_ANSWERS_DIR, str(answer_script_id))
    
    # Clear directory for idempotency
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Open PDF
        try:
            pdf_document = fitz.open(doc_path)
        except Exception as e:
            raise Exception(f"Failed to open PDF: {str(e)}")
            
        page_count = len(pdf_document)
        if page_count == 0:
            raise Exception("PDF contains zero pages")
            
        document.page_count = page_count
        
        # Process each page
        for i in range(page_count):
            page = pdf_document.load_page(i)
            pix = page.get_pixmap(dpi=300)  # 300 DPI required for handwriting OCR
            
            page_filename = f"page_{i+1:03d}.png"
            page_filepath = os.path.join(output_dir, page_filename)
            pix.save(page_filepath)
            
        pdf_document.close()
        
        document.processing_status = "processed"
        document.processed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(document)
        return document
        
    except Exception as e:
        document.processing_status = "failed"
        document.processing_error = str(e)
        db.commit()
        db.refresh(document)
        raise HTTPException(status_code=400, detail=f"Processing failed: {str(e)}")
