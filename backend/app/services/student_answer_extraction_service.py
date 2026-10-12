import re
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.answer_script import AnswerScript
from app.models.answer_script_page import AnswerScriptPage
from app.models.question import Question
from app.models.student_answer import StudentAnswer

def clean_ocr_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\bQl\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQi\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQO\b', 'Q0', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQ I\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQ-1\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'^l\.', '1.', text, flags=re.MULTILINE)
    text = re.sub(r'^I\.', '1.', text, flags=re.MULTILINE)
    return text

def extract_student_answers(answer_script_id: int, db: Session):
    # 1. Fetch script and verify
    script = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    if script.ocr_status != "processed":
        raise HTTPException(status_code=400, detail="OCR not processed for this script")
        
    # 2. Fetch exam questions
    questions = db.query(Question).filter(Question.exam_id == script.exam_id).all()
    if not questions:
        raise HTTPException(status_code=400, detail="No questions extracted for this exam")
        
    valid_q_nums = {q.question_number: q for q in questions}
    
    # 3. Fetch OCR pages
    pages = db.query(AnswerScriptPage).filter(
        AnswerScriptPage.answer_script_id == answer_script_id
    ).order_by(AnswerScriptPage.page_number).all()
    
    if not pages:
        raise HTTPException(status_code=400, detail="No OCR pages found")

    # Grouping logic
    # We will iterate through pages, detecting markers
    # Pattern is the same as phase 10
    pattern = r'(?:^|\n)(?:Q(\d+(?:\([a-z]\))?)[\.\)]?|Question No\.? (\d+(?:\([a-z]\))?)[\.\)]?|Question (\d+(?:\([a-z]\))?)[\.\)]?|(\d+(?:\([a-z]\))?)[\.\)])\s*'
    
    current_q_num = None
    current_text = []
    start_page = None
    
    # Structure to hold gathered answers
    # dict of q_num -> {"text": list of strings, "start": int, "end": int}
    answers_data = {}
    
    # First, let's just collect all text with page tracking
    # Actually, a single regex split across the entire document might lose page boundaries.
    # Let's parse page by page.
    for page in pages:
        text = clean_ocr_text(page.extracted_text)
        page_num = page.page_number
        
        # Find all question markers in this page
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        
        if not matches:
            # If no matches, this entire page belongs to current_q_num
            if current_q_num:
                answers_data[current_q_num]["text"].append(text.strip())
                answers_data[current_q_num]["end"] = page_num
        else:
            # There are markers in this page
            last_idx = 0
            for i, match in enumerate(matches):
                # The text before the first marker belongs to the previous question
                if i == 0 and match.start() > 0:
                    pre_text = text[0:match.start()].strip()
                    if current_q_num and pre_text:
                        answers_data[current_q_num]["text"].append(pre_text)
                        answers_data[current_q_num]["end"] = page_num
                        
                q_num = (match.group(1) or match.group(2) or match.group(3) or match.group(4)).strip()
                
                # We start a new question block
                # Determine end of this block
                next_start = matches[i+1].start() if i + 1 < len(matches) else len(text)
                block_text = text[match.end():next_start].strip()
                
                current_q_num = q_num
                
                if current_q_num not in answers_data:
                    answers_data[current_q_num] = {"text": [], "start": page_num, "end": page_num}
                else:
                    answers_data[current_q_num]["end"] = page_num
                    
                if block_text:
                    answers_data[current_q_num]["text"].append(block_text)
                    
    
    # 4. Save to Database
    # Delete existing to maintain idempotency
    db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == answer_script_id).delete()
    db.commit()
    
    results = []
    
    # Write matched questions
    for q_num, data in answers_data.items():
        if q_num in valid_q_nums:
            question = valid_q_nums[q_num]
            ans_text = "\n".join(data["text"]).strip()
            
            student_ans = StudentAnswer(
                answer_script_id=answer_script_id,
                question_id=question.id,
                answer_text=ans_text,
                start_page=data["start"],
                end_page=data["end"],
                answer_status="detected"
            )
            db.add(student_ans)
            results.append({
                "question_number": q_num,
                "question_id": question.id,
                "answer_text": ans_text,
                "start_page": data["start"],
                "end_page": data["end"],
                "status": "detected"
            })
        else:
            # Unmatched question number detected in text
            results.append({
                "question_number": q_num,
                "question_id": None,
                "answer_text": "\n".join(data["text"]).strip(),
                "start_page": data["start"],
                "end_page": data["end"],
                "status": "unmatched"
            })
            
    # Record unanswered questions
    detected_q_nums = set(answers_data.keys())
    for q_num, question in valid_q_nums.items():
        if q_num not in detected_q_nums:
            student_ans = StudentAnswer(
                answer_script_id=answer_script_id,
                question_id=question.id,
                answer_text=None,
                start_page=None,
                end_page=None,
                answer_status="unanswered"
            )
            db.add(student_ans)
            results.append({
                "question_number": q_num,
                "question_id": question.id,
                "answer_text": None,
                "start_page": None,
                "end_page": None,
                "status": "unanswered"
            })
            
    db.commit()
    
    # Sort results by question number length then alphabetically
    results.sort(key=lambda x: (len(str(x["question_number"])), str(x["question_number"])))
    
    return {
        "answer_script_id": answer_script_id,
        "student_id": script.student_id,
        "exam_id": script.exam_id,
        "answers": results
    }

def get_student_answers(answer_script_id: int, db: Session):
    script = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    answers = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == answer_script_id).all()
    
    results = []
    for ans in answers:
        q_num = ans.question.question_number if ans.question else "Unknown"
        results.append({
            "question_number": q_num,
            "question_id": ans.question_id,
            "answer_text": ans.answer_text,
            "start_page": ans.start_page,
            "end_page": ans.end_page,
            "status": ans.answer_status
        })
        
    results.sort(key=lambda x: (len(str(x["question_number"])), str(x["question_number"])))
    
    return {
        "answer_script_id": answer_script_id,
        "student_id": script.student_id,
        "exam_id": script.exam_id,
        "answers": results
    }
