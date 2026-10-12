import re
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.exam_document import ExamDocument
from app.models.ocr_result import OCRResult
from app.models.question import Question
from app.models.model_answer import ModelAnswer
from app.models.rubric import Rubric

def extract_information(exam_id: int, document_id: int, db: Session):
    document = db.query(ExamDocument).filter(
        ExamDocument.id == document_id, 
        ExamDocument.exam_id == exam_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found for exam {exam_id}")
        
    ocr_results = db.query(OCRResult).filter(
        OCRResult.document_id == document_id,
        OCRResult.ocr_status == "processed"
    ).order_by(OCRResult.page_number).all()
    
    if not ocr_results:
        raise HTTPException(status_code=400, detail="No processed OCR results found for this document")
        
    full_text = "\n".join([res.extracted_text for res in ocr_results if res.extracted_text])
    
    # OCR Cleanup
    # Replace 'Ql' with 'Q1', 'QO' with 'Q0', 'l.' with '1.' etc., safely on question markers.
    full_text = re.sub(r'\bQl\b', 'Q1', full_text, flags=re.IGNORECASE)
    full_text = re.sub(r'\bQi\b', 'Q1', full_text, flags=re.IGNORECASE)
    full_text = re.sub(r'\bQO\b', 'Q0', full_text, flags=re.IGNORECASE)
    full_text = re.sub(r'^l\.', '1.', full_text, flags=re.MULTILINE)
    full_text = re.sub(r'^I\.', '1.', full_text, flags=re.MULTILINE)
    
    doc_type = document.document_type
    
    if doc_type == "question_paper":
        return _extract_question_paper(exam_id, full_text, db)
    elif doc_type == "model_answer":
        return _extract_model_answer(exam_id, full_text, db)
    elif doc_type == "marks_rubric":
        return _extract_marks_rubric(exam_id, full_text, db)
    else:
        raise HTTPException(status_code=400, detail="Unsupported document type")

def _extract_question_paper(exam_id: int, text: str, db: Session):
    pattern = r'(?:^|\n)(?:Q(\d+(?:\([a-z]\))?)[\.\)]?|Question No\.? (\d+(?:\([a-z]\))?)[\.\)]?|Question (\d+(?:\([a-z]\))?)[\.\)]?|(\d+(?:\([a-z]\))?)[\.\)])\s*(.*?)(?=(?:(?:^|\n)(?:Q\d+|Question No\.? \d+|Question \d+|\d+[\.\)]))|$)'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    extracted = []
    
    for match in matches:
        q_num = (match.group(1) or match.group(2) or match.group(3) or match.group(4)).strip()
        q_content = match.group(5).strip()
        
        marks_match = re.search(r'(\d+)\s*[Mm]arks?|[Mm]arks?:\s*(\d+)|\((\d+)\)', q_content)
        max_marks = 0
        if marks_match:
            max_marks_str = marks_match.group(1) or marks_match.group(2) or marks_match.group(3)
            if max_marks_str:
                max_marks = int(max_marks_str)
                
        q_text = re.sub(r'(\d+)\s*[Mm]arks?|[Mm]arks?:\s*(\d+)|\((\d+)\)', '', q_content).strip()
        
        if not q_text:
            continue
            
        existing_q = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_number == q_num
        ).first()
        
        if existing_q:
            existing_q.question_text = q_text
            if max_marks > 0:
                existing_q.max_marks = max_marks
            db.commit()
            extracted.append(existing_q)
        else:
            new_q = Question(
                exam_id=exam_id,
                question_number=q_num,
                question_text=q_text,
                max_marks=max_marks
            )
            db.add(new_q)
            db.commit()
            db.refresh(new_q)
            extracted.append(new_q)
            
    return {
        "document_type": "question_paper",
        "questions": [
            {
                "question_number": q.question_number,
                "question_text": q.question_text,
                "max_marks": q.max_marks
            } for q in extracted
        ]
    }

def _extract_model_answer(exam_id: int, text: str, db: Session):
    pattern = r'(?:^|\n)(?:Q(\d+(?:\([a-z]\))?)[\.\)]?|Question No\.? (\d+(?:\([a-z]\))?)[\.\)]?|Question (\d+(?:\([a-z]\))?)[\.\)]?|(\d+(?:\([a-z]\))?)[\.\)])\s*(.*?)(?=(?:(?:^|\n)(?:Q\d+|Question No\.? \d+|Question \d+|\d+[\.\)]))|$)'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    extracted = []
    
    for match in matches:
        q_num = (match.group(1) or match.group(2) or match.group(3) or match.group(4)).strip()
        ans_text = match.group(5).strip()
        
        if not ans_text:
            continue
            
        q = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_number == q_num
        ).first()
        
        if not q:
            continue
            
        existing_ans = db.query(ModelAnswer).filter(ModelAnswer.question_id == q.id).first()
        if existing_ans:
            existing_ans.answer_text = ans_text
            db.commit()
            extracted.append({"question_number": q_num, "answer_text": ans_text})
        else:
            new_ans = ModelAnswer(question_id=q.id, answer_text=ans_text)
            db.add(new_ans)
            db.commit()
            extracted.append({"question_number": q_num, "answer_text": ans_text})
            
    return {
        "document_type": "model_answer",
        "model_answers": extracted
    }

def _extract_marks_rubric(exam_id: int, text: str, db: Session):
    pattern = r'(?:^|\n)(?:Q(\d+(?:\([a-z]\))?)[\.\)]?|Question No\.? (\d+(?:\([a-z]\))?)[\.\)]?|Question (\d+(?:\([a-z]\))?)[\.\)]?|(\d+(?:\([a-z]\))?)[\.\)])\s*(.*?)(?=(?:(?:^|\n)(?:Q\d+|Question No\.? \d+|Question \d+|\d+[\.\)]))|$)'
    matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
    
    extracted = []
    
    for match in matches:
        q_num = (match.group(1) or match.group(2) or match.group(3) or match.group(4)).strip()
        rubric_text = match.group(5).strip()
        
        q = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_number == q_num
        ).first()
        
        if not q:
            continue
            
        db.query(Rubric).filter(Rubric.question_id == q.id).delete()
        db.commit()
        
        lines = rubric_text.split('\n')
        q_rubrics = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            r_match = re.search(r'^(.*?)[-—:]\s*(\d+)\s*[Mm]arks?$', line, re.IGNORECASE)
            if r_match:
                criterion = r_match.group(1).strip()
                marks = int(r_match.group(2))
            else:
                r_match_2 = re.search(r'^(.*?)\s+(\d+)$', line)
                if r_match_2:
                    criterion = r_match_2.group(1).strip()
                    marks = int(r_match_2.group(2))
                else:
                    criterion = line
                    marks = 0
                    
            if criterion:
                r = Rubric(question_id=q.id, criterion=criterion, marks=marks)
                db.add(r)
                q_rubrics.append({"criterion": criterion, "marks": marks})
                
        db.commit()
        if q_rubrics:
            extracted.append({"question_number": q_num, "rubrics": q_rubrics})
            
    return {
        "document_type": "marks_rubric",
        "rubrics": extracted
    }
