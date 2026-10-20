import re
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.exam_document import ExamDocument
from app.models.ocr_result import OCRResult
from app.models.question import Question
from app.models.model_answer import ModelAnswer
from app.models.rubric import Rubric
from app.models.exam import Exam

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Shared: Broad handwriting & typed question marker patterns
# ─────────────────────────────────────────────────────────
_Q_MARKER = (
    r'(?:^|\n)\s*'
    r'(?:'
    r'Q\.?\s*(\d+[a-z]?)'                                                   # Q1, Q.1, Q1a
    r'|(?:Question|Ques|Ans(?:wer)?|Sol(?:ution)?)\s*[:\-\.]?\s*(?:No\.?\s*)?(\d+[a-z]?)'  # Question 1
    r'|\(?(\d+[a-z]?)\s*[\.:\)]'                                             # 1. or (1)
    r')'
)

_LOOKAHEAD = (
    r'\s*(.*?)(?='
    r'(?:\n\s*(?:Q\.?\s*\d+|(?:Question|Ques|Ans(?:wer)?|Sol(?:ution)?)\s*[:\-\.]?\s*(?:No\.?\s*)?\d+|\(?\d+[a-z]?\s*[\.:\)]))|$)'
)

FULL_PATTERN = _Q_MARKER + _LOOKAHEAD


def _get_q_num(match) -> str:
    return (match.group(1) or match.group(2) or match.group(3) or "").strip()


def _get_q_content(match) -> str:
    return (match.group(4) or "").strip()


def _ocr_cleanup(text: str) -> str:
    """Clean common OCR misreads of question markers from documents."""
    text = re.sub(r'\bQ[lI|]\b', 'Q1', text)
    text = re.sub(r'\bQi\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQO\b', 'Q0', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQ\s*-\s*(\d+)', r'Q\1', text)
    text = re.sub(r'\bQ\s+(\d+)\b', r'Q\1', text)
    text = re.sub(r'^l\.', '1.', text, flags=re.MULTILINE)
    text = re.sub(r'^I\.', '1.', text, flags=re.MULTILINE)
    return text


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
    full_text = _ocr_cleanup(full_text)

    doc_type = document.document_type

    if doc_type == "question_paper":
        return _extract_question_paper(exam_id, full_text, db)
    elif doc_type == "model_answer":
        return _extract_model_answer(exam_id, full_text, db)
    elif doc_type == "marks_rubric":
        return _extract_marks_rubric(exam_id, full_text, db)
    else:
        raise HTTPException(status_code=400, detail="Unsupported document type")


def _extract_marks_from_text(text: str, default: int = 10) -> int:
    """Extract marks allocation from question or document text."""
    marks_match = re.search(
        r'(\d+)\s*[- ]?[Mm]arks?|[Mm]arks?:\s*(\d+)|\[(\d+)\]|\((\d+)\s*[Mm]?\)',
        text,
        re.IGNORECASE
    )
    if marks_match:
        val = marks_match.group(1) or marks_match.group(2) or marks_match.group(3) or marks_match.group(4)
        if val:
            try:
                return int(val)
            except ValueError:
                pass
    return default


def _extract_question_paper(exam_id: int, text: str, db: Session):
    """
    Extract questions from a handwritten or typed question paper.
    Supports:
    1. Numbered questions (Q1, Q.1, Question 1, 1., (1), etc.)
    2. Single unnumbered questions (e.g. 'Q. Explain the A* search algorithm...', 'Question: ...')
    3. Fallback: Entire text treated as Q1 with total marks detected
    """
    matches = list(re.finditer(FULL_PATTERN, text, re.IGNORECASE | re.DOTALL | re.MULTILINE))
    extracted = []

    for match in matches:
        q_num = _get_q_num(match)
        q_content = _get_q_content(match)

        if not q_num or not q_content:
            continue

        max_marks = _extract_marks_from_text(q_content, default=10)
        q_text = re.sub(r'(\d+)\s*[- ]?[Mm]arks?|[Mm]arks?:\s*(\d+)|\[(\d+)\]|\((\d+)\s*[Mm]?\)', '', q_content, flags=re.IGNORECASE).strip()

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

    # ── FALLBACK FOR UN-NUMBERED SINGLE QUESTION PAPERS ──
    if not extracted:
        logger.info(f"Exam {exam_id}: No numbered question markers found. Attempting unnumbered question extraction.")
        
        # Look for 'Q. Explain...', 'Question: ...', or '10-Mark Question\n...'
        q_single = re.search(
            r'(?:^|\n)\s*(?:Q\.?\s*|Question\s*[:\-]?\s*)(.+?)(?=\n\s*(?:Marks?|Answer in|Total|Artificial Intelligence|\Z))',
            text,
            re.DOTALL | re.IGNORECASE
        )
        
        q_text = ""
        if q_single:
            q_text = q_single.group(1).strip()
        else:
            # Look for lines starting with question verbs
            verb_match = re.search(
                r'(?:^|\n)\s*((?:Explain|Discuss|Describe|Define|What is|Compare|Illustrate|Analyze|Evaluate)\b.+?)(?=\n\s*(?:Marks?|Answer in|Total|\Z))',
                text,
                re.DOTALL | re.IGNORECASE
            )
            if verb_match:
                q_text = verb_match.group(1).strip()
            else:
                # If still empty, take non-header lines
                clean_lines = [
                    line.strip() for line in text.split('\n')
                    if line.strip() and not re.search(r'Assessment|Semester|University|Internal|Duration|Page|Practice', line, re.IGNORECASE)
                ]
                q_text = " ".join(clean_lines[:4]).strip()

        if q_text:
            max_marks = _extract_marks_from_text(text, default=10)
            existing_q = db.query(Question).filter(
                Question.exam_id == exam_id,
                Question.question_number == "1"
            ).first()

            if existing_q:
                existing_q.question_text = q_text
                existing_q.max_marks = max_marks
                db.commit()
                extracted.append(existing_q)
            else:
                new_q = Question(
                    exam_id=exam_id,
                    question_number="1",
                    question_text=q_text,
                    max_marks=max_marks
                )
                db.add(new_q)
                db.commit()
                db.refresh(new_q)
                extracted.append(new_q)
            logger.info(f"Exam {exam_id}: Successfully extracted single question as Q1: '{q_text[:50]}...' ({max_marks} marks)")

    # Update Exam total marks if available
    if extracted:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if exam:
            total_calc = sum(q.max_marks for q in extracted)
            if not exam.total_marks or exam.total_marks != total_calc:
                exam.total_marks = total_calc
                db.commit()

    logger.info(f"Extracted {len(extracted)} questions from exam {exam_id} question paper")

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
    """
    Extract model answers from a handwritten or typed model answer sheet.
    Supports both numbered questions and single-question assignments.
    """
    exam_questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    if len(exam_questions) == 1:
        q = exam_questions[0]
        existing_ans = db.query(ModelAnswer).filter(ModelAnswer.question_id == q.id).first()
        if existing_ans:
            existing_ans.answer_text = text
            db.commit()
        else:
            new_ans = ModelAnswer(question_id=q.id, answer_text=text)
            db.add(new_ans)
            db.commit()
        logger.info(f"Exam {exam_id}: Assigned full model answer ({len(text.split())} words) to single question Q{q.question_number}")
        return {
            "document_type": "model_answer",
            "model_answers": [{"question_number": q.question_number, "answer_text": text}]
        }

    matches = list(re.finditer(FULL_PATTERN, text, re.IGNORECASE | re.DOTALL | re.MULTILINE))
    extracted = []

    for match in matches:
        q_num = _get_q_num(match)
        ans_text = _get_q_content(match)

        if not q_num or not ans_text:
            continue

        q = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_number == q_num
        ).first()

        if not q:
            norm = q_num.lstrip("0") or q_num
            q = db.query(Question).filter(
                Question.exam_id == exam_id,
                Question.question_number.ilike(norm)
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

    # ── FALLBACK: IF NO NUMBERED ANSWERS MATCHED, ASSIGN TO Q1 IF SINGLE QUESTION ──
    if not extracted:
        exam_questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        if len(exam_questions) == 1:
            q = exam_questions[0]
            existing_ans = db.query(ModelAnswer).filter(ModelAnswer.question_id == q.id).first()
            if existing_ans:
                existing_ans.answer_text = text
                db.commit()
                extracted.append({"question_number": q.question_number, "answer_text": text})
            else:
                new_ans = ModelAnswer(question_id=q.id, answer_text=text)
                db.add(new_ans)
                db.commit()
                extracted.append({"question_number": q.question_number, "answer_text": text})
            logger.info(f"Exam {exam_id}: Assigned full model answer to single question Q{q.question_number}")

    logger.info(f"Extracted {len(extracted)} model answers for exam {exam_id}")

    return {
        "document_type": "model_answer",
        "model_answers": extracted
    }


def _extract_marks_rubric(exam_id: int, text: str, db: Session):
    """
    Extract marking rubric from a handwritten or typed rubric document.
    Handles:
    1. Multi-question rubrics (Q1: Criterion - Marks, Q2: ...)
    2. Tabular criteria lines (e.g. 'Definition and purpose ... 1.0', 'Evaluation function ... 2.0')
    3. Bulleted / list criteria lines ('1. Definition - 2 marks')
    """
    matches = list(re.finditer(FULL_PATTERN, text, re.IGNORECASE | re.DOTALL | re.MULTILINE))
    extracted = []

    for match in matches:
        q_num = _get_q_num(match)
        rubric_text = _get_q_content(match)

        if not q_num:
            continue

        q = db.query(Question).filter(
            Question.exam_id == exam_id,
            Question.question_number == q_num
        ).first()

        if not q:
            norm = q_num.lstrip("0") or q_num
            q = db.query(Question).filter(
                Question.exam_id == exam_id,
                Question.question_number.ilike(norm)
            ).first()

        if not q:
            continue

        db.query(Rubric).filter(Rubric.question_id == q.id).delete()
        db.commit()

        q_rubrics = _parse_criteria_lines(q.id, rubric_text, db)
        if q_rubrics:
            extracted.append({"question_number": q_num, "rubrics": q_rubrics})

    # ── FALLBACK FOR TABULAR / UNNUMBERED RUBRICS ──
    if not extracted:
        exam_questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        if len(exam_questions) >= 1:
            q = exam_questions[0]
            db.query(Rubric).filter(Rubric.question_id == q.id).delete()
            db.commit()

            q_rubrics = _parse_criteria_lines(q.id, text, db)
            if q_rubrics:
                extracted.append({"question_number": q.question_number, "rubrics": q_rubrics})
                logger.info(f"Exam {exam_id}: Extracted {len(q_rubrics)} tabular rubric criteria for Q{q.question_number}")

    logger.info(f"Extracted rubrics for {len(extracted)} questions in exam {exam_id}")

    return {
        "document_type": "marks_rubric",
        "rubrics": extracted
    }


def _parse_criteria_lines(question_id: int, text: str, db: Session) -> list:
    """Parses individual criterion and mark allocations from rubric text or table."""
    lines = text.split('\n')
    q_rubrics = []

    for line in lines:
        line = line.strip()
        if not line or 'Criterion Expected evidence' in line or 'Total' in line or line.startswith('Note:'):
            continue

        criterion = ""
        marks = 0.0

        # Pattern 1: Table row with evidence description and mark at the end (e.g. '... 1.0', '... 2.0', '... 05')
        table_m = re.search(r'([A-Za-z][A-Za-z0-9 /_\-—|]+?)\s+(?:Defines|Correctly|Explains|Provides|States|Mentions|Presents|[-—:]).*?(\d+(?:\.\d+)?|05)\s*$', line)
        if table_m:
            criterion = table_m.group(1).replace('|', '').replace('_', '').strip()
            marks_str = table_m.group(2)
            marks = 0.5 if marks_str == '05' else float(marks_str)
        else:
            # Pattern 2: 'Criterion - 2 marks' or 'Criterion: 2'
            r_match = re.search(r'^(.*?)[-—:]\s*(\d+(?:\.\d+)?)\s*[Mm]arks?$', line, re.IGNORECASE)
            if r_match:
                criterion = r_match.group(1).strip()
                marks = float(r_match.group(2))
            else:
                # Pattern 3: 'Criterion 2' or '1. Criterion 2.0'
                r_match_2 = re.search(r'^(?:(?:\d+[\.\)]\s*)?)(.+?)\s+(\d+(?:\.\d+)?)$', line)
                if r_match_2 and not line.lower().startswith('question') and not line.lower().startswith('marks'):
                    criterion = r_match_2.group(1).strip()
                    marks = float(r_match_2.group(2))

        # Cleanup criterion string
        criterion = re.sub(r'^[\d\.\)\-\*\+•\|\s]+', '', criterion).strip()

        if criterion and marks > 0 and len(criterion) > 2:
            r = Rubric(question_id=question_id, criterion=criterion, marks=marks)
            db.add(r)
            q_rubrics.append({"criterion": criterion, "marks": marks})

    db.commit()
    return q_rubrics
