import os
import pytesseract
from PIL import Image
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
from app.models.exam_document import ExamDocument
from app.models.ocr_result import OCRResult
from app.config import settings

def process_document_ocr(document_id: int, db: Session):
    document = db.query(ExamDocument).filter(ExamDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.processing_status != "processed":
        raise HTTPException(status_code=400, detail="Document must be processed into pages before OCR can be run")
        
    exam_id = document.exam_id
    
    # Configure Tesseract path if available in settings
    tesseract_cmd = getattr(settings, "tesseract_cmd", os.environ.get("TESSERACT_CMD"))
    if tesseract_cmd and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    
    output_dir = os.path.join("uploads", "processed", "exams", str(exam_id), str(document_id))
    
    if not os.path.exists(output_dir):
        raise HTTPException(status_code=400, detail="Processed pages directory not found")
    
    # Idempotency: remove previous results
    db.query(OCRResult).filter(OCRResult.document_id == document_id).delete()
    db.commit()
    
    # Find pages
    page_files = sorted([f for f in os.listdir(output_dir) if f.endswith(".png") and f.startswith("page_")])
    if not page_files:
        raise HTTPException(status_code=400, detail="No processed page images found for OCR")
        
    for file_name in page_files:
        try:
            page_num = int(file_name.split("_")[1].split(".")[0])
        except Exception:
            continue
            
        image_path = os.path.join(output_dir, file_name)
        
        ocr_res = OCRResult(
            document_id=document_id,
            page_number=page_num,
            image_path=image_path,
            ocr_status="processing"
        )
        db.add(ocr_res)
        db.commit()
        db.refresh(ocr_res)
        
        try:
            # Basic preprocessing/OCR
            img = Image.open(image_path)
            
            # Grayscale
            img = img.convert('L')
            
            text = pytesseract.image_to_string(img)
            
            ocr_res.extracted_text = text
            ocr_res.ocr_status = "processed"
            ocr_res.processed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as e:
            ocr_res.ocr_status = "failed"
            ocr_res.error_message = str(e)
            db.commit()
            
    # Return overall result
    results = db.query(OCRResult).filter(OCRResult.document_id == document_id).order_by(OCRResult.page_number).all()
    
    status = "processed"
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

from app.models.answer_script import AnswerScript
from app.models.answer_script_page import AnswerScriptPage
from app.services.document_processing_service import PROCESSED_ANSWERS_DIR

def process_answer_script_ocr(answer_script_id: int, db: Session):
    document = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    if document.processing_status != "processed":
        raise HTTPException(status_code=400, detail="Answer script images have not been processed yet")
        
    image_dir = os.path.join(PROCESSED_ANSWERS_DIR, str(answer_script_id))
    if not os.path.exists(image_dir):
        raise HTTPException(status_code=400, detail="Processed images directory not found")
        
    db.query(AnswerScriptPage).filter(AnswerScriptPage.answer_script_id == answer_script_id).delete()
    db.commit()
    
    document.ocr_status = "processing"
    db.commit()
    
    try:
        pages_processed = 0
        for i in range(document.page_count):
            page_num = i + 1
            filename = f"page_{page_num:03d}.png"
            filepath = os.path.join(image_dir, filename)
            
            if not os.path.exists(filepath):
                continue
                
            img = Image.open(filepath).convert("L")
            text = pytesseract.image_to_string(img)
            
            ocr_res = AnswerScriptPage(
                answer_script_id=answer_script_id,
                page_number=page_num,
                image_path=filepath,
                extracted_text=text,
                ocr_status="processed",
                processed_at=datetime.now(timezone.utc)
            )
            db.add(ocr_res)
            pages_processed += 1
            
        document.ocr_status = "processed"
        db.commit()
        
    except Exception as e:
        document.ocr_status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")
        
def get_answer_script_ocr_results(answer_script_id: int, db: Session):
    document = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    results = db.query(AnswerScriptPage).filter(AnswerScriptPage.answer_script_id == answer_script_id).order_by(AnswerScriptPage.page_number).all()
    
    return {
        "answer_script_id": answer_script_id,
        "student_id": document.student_id,
        "exam_id": document.exam_id,
        "status": document.ocr_status,
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
