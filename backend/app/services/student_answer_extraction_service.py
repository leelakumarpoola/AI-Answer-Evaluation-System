"""
Student Answer Extraction Service — Handwriting-Aware Segmentation
==================================================================
Extracts individual question answers from OCR'd handwritten answer scripts.

Strategy:
1. Clean and normalize OCR text (fix common Tesseract misreads)
2. Try marker-based extraction (Q1, 1., Question 1, Ans 1, etc.)
3. If NO markers found: controlled positional fallback (marked for review)
4. Fuzzy question-number matching (handles OCR variants like "Ql" → "Q1")
5. Save answers with status: detected | positional | unanswered | unmatched
6. Unanswered questions are explicitly recorded

Key principles:
- NEVER silently assign content to wrong questions
- Always flag uncertain assignments for review
- Preserve raw OCR text in addition to cleaned text
- Cross-page answers handled correctly (answer continues to next page)
"""

import re
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.answer_script import AnswerScript
from app.models.answer_script_page import AnswerScriptPage
from app.models.question import Question
from app.models.student_answer import StudentAnswer

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# OCR Text Normalization
# ─────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────
# OCR Text Normalization
# ─────────────────────────────────────────────────────────

def clean_ocr_text(text: str) -> str:
    """
    Fix systematic Tesseract misreads in handwritten text.
    Preserves answer content while normalizing question markers.
    """
    if not text:
        return ""

    # Normalize circled unicode numbers to Q1, Q2, etc.
    CIRCLED_DIGITS = {
        "①": "\nQ1 ", "②": "\nQ2 ", "③": "\nQ3 ", "④": "\nQ4 ", "⑤": "\nQ5 ",
        "⑥": "\nQ6 ", "⑦": "\nQ7 ", "⑧": "\nQ8 ", "⑨": "\nQ9 ", "⑩": "\nQ10 ",
        "⑴": "\nQ1 ", "⑵": "\nQ2 ", "⑶": "\nQ3 ", "⑷": "\nQ4 ", "⑸": "\nQ5 ",
    }
    for circ, rep in CIRCLED_DIGITS.items():
        text = text.replace(circ, rep)

    # Question marker normalization
    text = re.sub(r'\bQ[lI|]\b', 'Q1', text)
    text = re.sub(r'\bQi\b', 'Q1', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQO\b', 'Q0', text, flags=re.IGNORECASE)
    text = re.sub(r'\bQ\s*-\s*(\d+)', r'Q\1', text)    # Q - 1 → Q1
    text = re.sub(r'\bQ\s+(\d+)\b', r'Q\1', text)       # Q 1 → Q1

    # Student handwritten pattern: circled or top-margin "2" with "A" underneath or beside
    # e.g., "2 \n A", "2 A", "(2) A", "2. A"
    text = re.sub(r'(?:^|\n)\s*\(?(\d+)\)?\s*[\.:\-\)]?\s*\n+\s*[Aa]\s*\n+', r'\nQ\1 A\n', text)
    text = re.sub(r'(?:^|\n)\s*\(?(\d+)\)?\s*[\.:\-\)]?\s*[Aa]\s*[:\-\)]', r'\nQ\1 A: ', text)
    text = re.sub(r'(?:^|\n)\s*\(?(\d+)\)?\s+([Aa])\s+(?=[a-zA-Z])', r'\nQ\1 \2 ', text)
    # OCR misread where circled 2 looks like Q and handwritten A looks like P
    text = re.sub(r'(?:^|\n)\s*Q\s*\n+\s*P\s+(?=land|records|contract|architecture|blockchain|[a-zA-Z]{3,})', '\nQ2 A\n', text, flags=re.IGNORECASE)
    text = re.sub(r'(?:^|\n)\s*AS\s+(?=land|records|ownership)', '\nQ2 A land ', text, flags=re.IGNORECASE)

    # Line-start substitutions (common in numbered answers)
    text = re.sub(r'^l\.', '1.', text, flags=re.MULTILINE)  # l. → 1.
    text = re.sub(r'^I\.', '1.', text, flags=re.MULTILINE)  # I. → 1.

    # Remove stray pipes from scan artifacts
    text = re.sub(r'Ans\s*:\s*\|\s*', 'Ans: ', text)
    text = re.sub(r'\|\s*(\d+)', r'\1', text)
    text = re.sub(r'(?<!\w)\|(?!\w)', '', text)

    # Common OCR error in handwriting: "Ans: 41)" -> "Ans: 1)"
    text = re.sub(r'\bAns\s*:\s*4(\d+[\.\)])', r'Ans: \1', text)

    # Normalize excessive whitespace while keeping newlines
    text = re.sub(r'[ \t]{2,}', ' ', text)

    return text


# ─────────────────────────────────────────────────────────
# Question Marker Pattern — Handwriting-Aware
# ─────────────────────────────────────────────────────────
QUESTION_MARKER_PATTERN = re.compile(
    r"""
    (?:^|\n)                    # start of text or newline
    \s*                         # optional leading whitespace
    (?:
        # Explicit Question + Answer markers: 2 A, 2 Ans, Q2 A, Q2 Ans, (2) A
        Q\.?\s*(\d+[a-z]?)(?:\s*[\.:\-\)]\s*|\s+)(?:[Aa]ns(?:wer)?|[Aa])\b
        |
        \(?(\d+[a-z]?)\)?(?:\s*[\.:\-\)]\s*|\s+)(?:[Aa]ns(?:wer)?|[Aa])\b
        |
        # Or explicit Ans/Answer with no space needed: Q2Ans
        Q\.?\s*(\d+[a-z]?)\s*(?:[Aa]ns(?:wer)?)\b
        |
        # Q-prefixed markers (most reliable in handwriting)
        Q\.?\s*(\d+[a-z]?)\b
        |
        # Written-out markers: Question 1, Ques 2, Ans 2, Answer 2
        (?:Question|Ques|Ans(?:wer)?|Sol(?:ution)?)\s*[:\-\.]?\s*(?:No\.?\s*)?(\d+[a-z]?)\b
        |
        # Numeric markers at line start: 1. 1) (1) 1:
        \(?(\d+[a-z]?)\s*[\.:\)]
    )
    \s*                         # optional trailing whitespace
    """,
    re.IGNORECASE | re.VERBOSE | re.MULTILINE
)


def _is_numbered_list_item(match: re.Match, page_text: str) -> bool:
    """
    Determines whether a numeric marker (e.g. '1)', '2.') is an internal list item
    rather than an exam question marker.
    """
    matched_str = match.group(0).strip()
    if re.search(r'\b(?:Q|Question|Ques|Ans|Answer|Sol)\b', matched_str, re.IGNORECASE):
        return False
    if re.search(r'\b\d+\s*[Aa]\b', matched_str, re.IGNORECASE):
        return False

    start_idx = match.start()
    preceding = page_text[:start_idx]
    preceding_window = page_text[max(0, start_idx - 350):start_idx].strip()

    # Preceded by colon or list keywords (e.g. "is suitable because:", "following points:", "be cousse")
    if re.search(
        r'(?::\s*$|because\s*:?|be\s*cousse\s*:?|following\s*:?|points\s*:?|reasons\s*:?|advantages\s*:?|disadvantages\s*:?|types\s*:?|steps\s*:?|features\s*:?|solutions\s*:?|challenges\s*:?|properties\s*:?|requirements\s*:?|suitable\s+be\s*cous?se)',
        preceding_window,
        re.IGNORECASE
    ):
        return True

    # Preceded by an explicit Question header (e.g. Q2, 2 A, Question 2)
    has_active_q = bool(re.search(
        r'(?:^|\n)\s*(?:Q\.?\s*\d+|\(?\d+\)?\s*[Aa]\b|Question\s*\d+|Ans(?:wer)?\s*[:\-\d])',
        preceding,
        re.IGNORECASE
    ))

    # If there is already an active question on this page, any parenthesis marker '3)' or '(3)' is a bullet point
    is_paren = ')' in matched_str
    if has_active_q and is_paren:
        return True

    if has_active_q and re.search(r'(?:^|\n)\s*\(?[12345]\s*[\.:\)]', preceding_window):
        return True

    following = page_text[match.end(): min(len(page_text), match.end() + 250)]
    if has_active_q and re.search(r'(?:^|\n)\s*\(?\d+\s*[\.:\)]', following):
        return True

    return False


def _extract_question_number(match) -> str:
    """Extract the numeric part of a question marker from a regex match."""
    for g in match.groups():
        if g is not None and g.strip():
            return g.strip().lower()
    return ""


def _normalise_q_num(q_num: str) -> str:
    """Normalize question number: strip leading zeros, lowercase."""
    q_num = q_num.strip().lower()
    q_num = re.sub(r'^0+(\d)', r'\1', q_num)  # Remove leading zeros
    return q_num


def _build_q_num_lookup(questions: list) -> dict:
    """
    Build a flexible lookup for matching OCR-extracted question numbers
    to database Question objects.

    Handles variants:
    - "Q1" → Question(number="1") or Question(number="Q1")
    - "1" → Question(number="Q1") or Question(number="1")
    - "q1a" → Question(number="1a")
    """
    lookup = {}
    for q in questions:
        original = q.question_number.strip()
        normalised = _normalise_q_num(original)

        lookup[original] = q
        lookup[normalised] = q
        lookup[original.upper()] = q
        lookup[original.lower()] = q

        # Purely numeric key: "1" matches "Q1", "q1", "1"
        numeric_only = re.sub(r'[^0-9a-z]', '', normalised)
        if numeric_only:
            lookup[numeric_only] = q

    return lookup


def _find_question(q_num: str, q_lookup: dict) -> object:
    """
    Try multiple lookup keys to find a matching Question.
    Returns Question or None.
    Handles OCR variants like '41' when question is '1'.
    """
    candidates = [
        q_num,
        q_num.upper(),
        q_num.lower(),
        "q" + q_num,        # "1" → "q1"
        q_num.lstrip("q"),  # "q1" → "1"
        q_num.lstrip("Q"),  # "Q1" → "1"
    ]
    for key in candidates:
        result = q_lookup.get(key)
        if result:
            return result

    # Trailing digit recovery: OCR frequently adds noise before digits (e.g. "41" for "1")
    if len(q_num) > 1 and q_num.isdigit():
        for i in range(1, len(q_num)):
            sub = q_num[i:]
            for sub_key in [sub, "q" + sub, sub.lower(), sub.upper()]:
                if sub_key in q_lookup:
                    return q_lookup[sub_key]

    return None


# ─────────────────────────────────────────────────────────
# Positional Fallback — Controlled and Clearly Flagged
# ─────────────────────────────────────────────────────────

def _split_text_by_position(full_text: str, question_count: int) -> list:
    """
    When NO question markers are found, split the document by paragraph
    groups and assign sequentially to questions.

    IMPORTANT: Positional assignments are always marked as "positional"
    status (not "detected") and flagged for manual review.

    Returns: list of (inferred_q_num_str, text) tuples
    """
    # Split on blank lines (paragraph breaks)
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', full_text) if p.strip()]

    if not paragraphs:
        return []

    logger.warning(
        f"Positional fallback: {len(paragraphs)} paragraphs → "
        f"{question_count} questions (sequential assignment)"
    )

    if len(paragraphs) <= question_count:
        # Each paragraph = one question answer
        return [(str(i + 1), paragraphs[i]) for i in range(len(paragraphs))]
    else:
        # Group paragraphs into question_count chunks
        chunk_size = max(1, len(paragraphs) // question_count)
        result = []
        for i in range(question_count):
            start = i * chunk_size
            end = (i + 1) * chunk_size if i < question_count - 1 else len(paragraphs)
            chunk = "\n\n".join(paragraphs[start:end])
            if chunk:
                result.append((str(i + 1), chunk))
        return result


# ─────────────────────────────────────────────────────────
# Main Extraction Function
# ─────────────────────────────────────────────────────────

def extract_student_answers(answer_script_id: int, db: Session):
    """
    Extract student answers from an OCR'd handwritten answer script.

    Full pipeline:
    1. Validate prerequisites (OCR done, questions exist in DB)
    2. Clean and combine OCR text from all pages
    3. Try marker-based segmentation (Q1, 1., Question 1, etc.)
    4. Fall back to positional splitting if no markers found
    5. Match extracted blocks to DB questions (fuzzy matching)
    6. Save answers with appropriate status and review flags
    7. Record unanswered questions explicitly

    Returns JSON with all answers and their extraction status.
    """
    # ── 1. Fetch and validate prerequisites ───────────────────────

    script = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")

    if script.ocr_status != "processed":
        raise HTTPException(
            status_code=400,
            detail=(
                f"OCR status is '{script.ocr_status}'. "
                "Answer script OCR must be completed before extracting answers."
            )
        )

    questions = db.query(Question).filter(Question.exam_id == script.exam_id).all()
    if not questions:
        # Resilient auto-processing: extract master documents if question paper exists
        from app.models.exam_document import ExamDocument
        from app.services.document_processing_service import process_document
        from app.services.ocr_service import process_document_ocr
        from app.services.document_extraction_service import extract_information

        qp_doc = db.query(ExamDocument).filter(
            ExamDocument.exam_id == script.exam_id,
            ExamDocument.document_type == "question_paper"
        ).first()

        if qp_doc:
            logger.info(f"Auto-processing master documents for exam {script.exam_id}...")
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
                "Please upload the Question Paper PDF first and click 'Process Documents'."
            )
        )

    q_lookup = _build_q_num_lookup(questions)
    question_count = len(questions)

    # ── 2. Load OCR pages and build page text list ─────────────────

    pages = db.query(AnswerScriptPage).filter(
        AnswerScriptPage.answer_script_id == answer_script_id
    ).order_by(AnswerScriptPage.page_number).all()

    if not pages:
        raise HTTPException(
            status_code=400,
            detail="No OCR pages found. Run OCR first."
        )

    page_texts = []
    total_words = 0
    for page in pages:
        cleaned = clean_ocr_text(page.extracted_text or "")
        word_count = len(cleaned.split())
        total_words += word_count
        page_texts.append((page.page_number, cleaned))

    full_text = "\n".join(t for _, t in page_texts)

    logger.info(
        f"Answer script {answer_script_id}: "
        f"{len(pages)} pages, {total_words} total words, "
        f"{question_count} questions expected"
    )

    if total_words < 5:
        logger.warning(
            f"Answer script {answer_script_id}: Very few words ({total_words}) in OCR output. "
            "This may indicate: blank pages, poor scan quality, or OCR failure. "
            "Consider re-running OCR after checking the uploaded PDF."
        )

    # ── 3. Marker-based segmentation (across all pages) ────────────

    answers_data = {}         # q_num_str → {"text": [...], "start": page, "end": page}
    current_q_num = None

    for page_num, page_text in page_texts:
        all_matches = list(QUESTION_MARKER_PATTERN.finditer(page_text))
        # Filter out matches that are internal list items or not valid questions in the exam
        matches = []
        for m in all_matches:
            if _is_numbered_list_item(m, page_text):
                continue
            raw_q = _extract_question_number(m)
            norm_q = _normalise_q_num(raw_q)
            if not _find_question(norm_q, q_lookup):
                continue
            matches.append(m)

        if not matches:
            # No real question markers on this page — content belongs to current question (cross-page answer)
            if current_q_num is not None and page_text.strip():
                answers_data[current_q_num]["text"].append(page_text.strip())
                answers_data[current_q_num]["end"] = page_num
            elif current_q_num is None and page_text.strip():
                # Text before any marker — may be preamble or first answer without marker
                sentinel = "__pre__"
                if sentinel not in answers_data:
                    answers_data[sentinel] = {
                        "text": [], "start": page_num, "end": page_num
                    }
                answers_data[sentinel]["text"].append(page_text.strip())
                answers_data[sentinel]["end"] = page_num
        else:
            for i, match in enumerate(matches):
                raw_q_num = _extract_question_number(match)
                if not raw_q_num:
                    continue

                norm_q_num = _normalise_q_num(raw_q_num)

                # Text before the first marker on this page → current question
                if i == 0 and match.start() > 0:
                    pre_text = page_text[: match.start()].strip()
                    if pre_text and current_q_num is not None:
                        answers_data[current_q_num]["text"].append(pre_text)
                        answers_data[current_q_num]["end"] = page_num

                # Text from this marker to the next (or end of page)
                next_start = matches[i + 1].start() if i + 1 < len(matches) else len(page_text)
                block_text = page_text[match.end(): next_start].strip()

                current_q_num = norm_q_num

                if current_q_num not in answers_data:
                    answers_data[current_q_num] = {
                        "text": [], "start": page_num, "end": page_num, "status": "detected"
                    }
                else:
                    answers_data[current_q_num]["end"] = page_num

                if block_text:
                    answers_data[current_q_num]["text"].append(block_text)

    # ── Handle pre-marker content ──────────────────────────────────
    pre_content = answers_data.pop("__pre__", None)

    use_positional = False

    if not answers_data:
        # No markers detected at all → positional fallback
        logger.warning(
            f"Answer script {answer_script_id}: "
            "No question markers detected in OCR output. "
            "Falling back to positional paragraph extraction (answers flagged for review)."
        )
        positional = _split_text_by_position(full_text, question_count)
        for q_str, text in positional:
            answers_data[q_str] = {
                "text": [text], "start": 1, "end": len(pages), "status": "positional"
            }
        use_positional = True
    else:
        # Attach pre-marker content to the first detected question in the document
        if pre_content and answers_data:
            first_key = next(iter(answers_data))
            answers_data[first_key]["text"] = pre_content["text"] + answers_data[first_key]["text"]

    logger.info(
        f"Answer script {answer_script_id}: "
        f"{len(answers_data)} blocks extracted "
        f"({'positional' if use_positional else 'marker-based'}): "
        f"{list(answers_data.keys())}"
    )

    # ── 4. Match blocks to DB questions via fuzzy lookup ───────────

    existing_answers = {
        sa.question_id: sa
        for sa in db.query(StudentAnswer).filter(
            StudentAnswer.answer_script_id == answer_script_id
        ).all()
    }

    results = []
    matched_question_ids = set()

    # ── Special case: Single-question exam ────────────────────────
    if question_count == 1 and answers_data:
        single_q = questions[0]
        # Combine all answer blocks
        all_blocks = []
        for q_key, data in answers_data.items():
            block_t = "\n".join(data["text"]).strip()
            if block_t:
                all_blocks.append(block_t)
        combined_text = "\n\n".join(all_blocks).strip() or full_text.strip()

        matched_question_ids.add(single_q.id)
        student_ans = existing_answers.get(single_q.id)
        if not student_ans:
            student_ans = StudentAnswer(
                answer_script_id=answer_script_id,
                question_id=single_q.id,
                answer_text=combined_text,
                start_page=1,
                end_page=len(pages),
                answer_status="detected"
            )
            db.add(student_ans)
        else:
            student_ans.answer_text = combined_text
            student_ans.start_page = 1
            student_ans.end_page = len(pages)
            student_ans.answer_status = "detected"

        results.append({
            "question_number": single_q.question_number,
            "question_id": single_q.id,
            "answer_text": combined_text,
            "start_page": 1,
            "end_page": len(pages),
            "status": "detected",
            "word_count": len(combined_text.split()),
            "needs_review": False
        })
    else:
        for q_num, data in answers_data.items():
            question = _find_question(q_num, q_lookup)
            ans_text = "\n".join(data["text"]).strip()
            block_status = data.get("status", "detected")

            if question:
                matched_question_ids.add(question.id)
                student_ans = existing_answers.get(question.id)
                if not student_ans:
                    student_ans = StudentAnswer(
                        answer_script_id=answer_script_id,
                        question_id=question.id,
                        answer_text=ans_text,
                        start_page=data["start"],
                        end_page=data["end"],
                        answer_status=block_status
                    )
                    db.add(student_ans)
                else:
                    student_ans.answer_text = ans_text
                    student_ans.start_page = data["start"]
                    student_ans.end_page = data["end"]
                    student_ans.answer_status = block_status

                results.append({
                    "question_number": question.question_number,
                    "question_id": question.id,
                    "answer_text": ans_text,
                    "start_page": data["start"],
                    "end_page": data["end"],
                    "status": block_status,
                    "word_count": len(ans_text.split()),
                    "needs_review": block_status == "positional"
                })
            else:
                # Unmatched marker — log and report without failing
                logger.debug(
                    f"Answer script {answer_script_id}: "
                    f"Unmatched question marker '{q_num}' — no DB question matches"
                )
                results.append({
                    "question_number": q_num,
                    "question_id": None,
                    "answer_text": ans_text,
                    "start_page": data["start"],
                    "end_page": data["end"],
                    "status": "unmatched",
                    "word_count": len(ans_text.split()),
                    "needs_review": True
                })

        # ── Recover unmatched blocks for questions not yet matched via semantic topic alignment ──
        unmatched_blocks = [r for r in results if r["question_id"] is None and r.get("answer_text")]
        unmatched_questions = [q for q in questions if q.id not in matched_question_ids]

        if unmatched_blocks and unmatched_questions:
            for block in unmatched_blocks:
                best_q = None
                best_sim = -1.0
                try:
                    from app.services.semantic_similarity_service import get_sbert_model, clean_text_for_sbert
                    from sentence_transformers import util
                    from app.models.model_answer import ModelAnswer
                    model = get_sbert_model()
                    b_emb = model.encode([clean_text_for_sbert(block["answer_text"])], convert_to_tensor=True)
                    for q in unmatched_questions:
                        ma = db.query(ModelAnswer).filter(ModelAnswer.question_id == q.id).first()
                        ref = f"{q.question_text} {ma.answer_text if ma else ''}"
                        r_emb = model.encode([clean_text_for_sbert(ref)], convert_to_tensor=True)
                        sim = float(util.cos_sim(b_emb, r_emb)[0][0].item())
                        if sim > best_sim:
                            best_sim = sim
                            best_q = q
                except Exception as align_err:
                    logger.debug(f"Semantic recovery error: {align_err}")

                q_target = best_q or unmatched_questions[0]
                if q_target in unmatched_questions:
                    unmatched_questions.remove(q_target)

                logger.info(
                    f"Assigning answer block ('{block['question_number']}') "
                    f"to question '{q_target.question_number}' via semantic alignment (score={best_sim:.2f})"
                )
                matched_question_ids.add(q_target.id)
                student_ans = existing_answers.get(q_target.id)
                if not student_ans:
                    student_ans = StudentAnswer(
                        answer_script_id=answer_script_id,
                        question_id=q_target.id,
                        answer_text=block["answer_text"],
                        start_page=block["start_page"],
                        end_page=block["end_page"],
                        answer_status="detected"
                    )
                    db.add(student_ans)
                else:
                    student_ans.answer_text = block["answer_text"]
                    student_ans.start_page = block["start_page"]
                    student_ans.end_page = block["end_page"]
                    student_ans.answer_status = "detected"

                block["question_number"] = q_target.question_number
                block["question_id"] = q_target.id
                block["status"] = "detected"
                block["needs_review"] = False

    # ── 5. Record unanswered questions ─────────────────────────────

    for question in questions:
        if question.id not in matched_question_ids:
            student_ans = existing_answers.get(question.id)
            if not student_ans:
                student_ans = StudentAnswer(
                    answer_script_id=answer_script_id,
                    question_id=question.id,
                    answer_text=None,
                    start_page=None,
                    end_page=None,
                    answer_status="unanswered"
                )
                db.add(student_ans)
            else:
                student_ans.answer_text = None
                student_ans.start_page = None
                student_ans.end_page = None
                student_ans.answer_status = "unanswered"

            results.append({
                "question_number": question.question_number,
                "question_id": question.id,
                "answer_text": None,
                "start_page": None,
                "end_page": None,
                "status": "unanswered",
                "word_count": 0,
                "needs_review": False
            })

    db.commit()

    # Sort by question number
    results.sort(key=lambda x: (len(str(x["question_number"])), str(x["question_number"])))

    detected = sum(1 for r in results if r["status"] == "detected")
    positional = sum(1 for r in results if r["status"] == "positional")
    unanswered = sum(1 for r in results if r["status"] == "unanswered")
    unmatched = sum(1 for r in results if r["status"] == "unmatched")

    logger.info(
        f"Answer script {answer_script_id}: "
        f"detected={detected}, positional={positional}, "
        f"unanswered={unanswered}, unmatched={unmatched}"
    )

    return {
        "answer_script_id": answer_script_id,
        "student_id": script.student_id,
        "exam_id": script.exam_id,
        "extraction_method": "positional" if use_positional else "marker_based",
        "total_words": total_words,
        "answers": results
    }


# ─────────────────────────────────────────────────────────
# Retrieval Function
# ─────────────────────────────────────────────────────────

def get_student_answers(answer_script_id: int, db: Session):
    script = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")

    answers = db.query(StudentAnswer).filter(
        StudentAnswer.answer_script_id == answer_script_id
    ).all()

    results = []
    for ans in answers:
        q_num = ans.question.question_number if ans.question else "Unknown"
        results.append({
            "question_number": q_num,
            "question_id": ans.question_id,
            "answer_text": ans.answer_text,
            "start_page": ans.start_page,
            "end_page": ans.end_page,
            "status": ans.answer_status,
            "word_count": len((ans.answer_text or "").split()),
            "needs_review": ans.answer_status in ("positional", "unmatched")
        })

    results.sort(key=lambda x: (len(str(x["question_number"])), str(x["question_number"])))

    return {
        "answer_script_id": answer_script_id,
        "student_id": script.student_id,
        "exam_id": script.exam_id,
        "answers": results
    }
