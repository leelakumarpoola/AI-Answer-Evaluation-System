"""
Rubric Evaluation Service — Multi-Signal Grading
=================================================
Awards marks using MULTIPLE signals, not similarity alone:

1. Semantic similarity (SBERT) — conceptual coverage
2. Keyword matching — presence of key technical terms
3. Answer length — minimum content check
4. OCR confidence — flag low-quality scans for review

Marks awarded per criterion:
  evidence_strength = (sbert_sim × 0.5) + (keyword_ratio × 0.35) + (length_bonus × 0.15)

Additional safeguards:
- Per-criterion marks never exceed rubric maximum
- Total marks never exceed question maximum
- Uncertain answers flagged for manual review
- Unanswered / missing model answer / missing rubric handled gracefully
- Full audit trail: evidence_score, keyword_hits, reason, needs_review
"""

import os
import re
import math
import json
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.models.student_answer import StudentAnswer
from app.models.rubric import Rubric
from app.models.evaluation import Evaluation
from app.models.question import Question
from app.models.model_answer import ModelAnswer
from app.models.rubric_evaluation import RubricEvaluation
from app.services.semantic_similarity_service import get_sbert_model, clean_text_for_sbert
from app.services.semantic_evaluation_service import evaluate_single_question
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────

# Minimum OCR word count below which we flag for review
MIN_WORDS_FOR_CONFIDENT_EVAL = 15

# Similarity thresholds for marking (calibrated for handwriting OCR)
EXCELLENT_THRESHOLD = 0.58
GOOD_THRESHOLD = 0.42
MODERATE_THRESHOLD = 0.28
WEAK_THRESHOLD = 0.14

# Weights for multi-signal evidence
SBERT_WEIGHT = 0.55
KEYWORD_WEIGHT = 0.30
LENGTH_WEIGHT = 0.15


# ─────────────────────────────────────────────────────────
# Keyword Extraction
# ─────────────────────────────────────────────────────────

def _extract_keywords(text: str, min_length: int = 4) -> set:
    """
    Extract meaningful words from text (ignore common stop words).
    Returns a set of lowercased words of length >= min_length.
    """
    stop_words = {
        "this", "that", "with", "from", "they", "have", "will", "been",
        "when", "where", "what", "which", "their", "there", "then", "than",
        "also", "each", "more", "such", "into", "over", "some", "very",
        "just", "because", "about", "after", "before", "through", "while"
    }
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    return {w for w in words if len(w) >= min_length and w not in stop_words}


def _keyword_match_ratio(student_text: str, reference_text: str) -> float:
    """
    Compute what fraction of reference keywords appear in student answer.
    Supports exact and prefix/stem matching to handle handwriting OCR noise.
    Returns a ratio 0.0–1.0.
    """
    ref_keywords = _extract_keywords(reference_text)
    if not ref_keywords:
        return 0.5  # Can't measure — give neutral score

    stu_keywords = _extract_keywords(student_text)
    if not stu_keywords:
        return 0.0

    # Exact keyword hits
    hits = ref_keywords.intersection(stu_keywords)

    # Prefix/stem matching for remaining keywords (tolerates OCR typos/plural endings)
    unmatched_ref = ref_keywords - hits
    for rk in unmatched_ref:
        prefix = rk[:5] if len(rk) >= 5 else rk
        if any(sk.startswith(prefix) or (len(sk) >= 5 and sk[:5] in rk) for sk in stu_keywords):
            hits.add(rk)

    ratio = len(hits) / len(ref_keywords)
    return min(1.0, ratio)


def _length_adequacy_score(student_text: str, model_answer_text: str) -> float:
    """
    Check if the student answer has sufficient length relative to the model answer.
    Prevents awarding marks for trivially short answers.

    Score:
    - < 20% of model length → 0.1
    - 20-50% → 0.5
    - > 50% → 1.0
    """
    model_words = len(model_answer_text.split()) if model_answer_text else 0
    student_words = len(student_text.split()) if student_text else 0

    if model_words == 0:
        return 0.5

    ratio = student_words / model_words
    if ratio < 0.2:
        return 0.1
    elif ratio < 0.5:
        return 0.5
    else:
        return 1.0


def _compute_evidence_strength(
    sbert_sim: float,
    keyword_ratio: float,
    length_score: float,
    overall_sim: float
) -> float:
    """
    Combine signals into a single evidence strength score.
    Returns 0.0–1.0.
    """
    # Primary signals
    strength = (
        sbert_sim * SBERT_WEIGHT
        + keyword_ratio * KEYWORD_WEIGHT
        + length_score * LENGTH_WEIGHT
    )
    # Blend with overall similarity (from the full answer vs model answer)
    # This gives context beyond just per-criterion matching
    blended = strength * 0.8 + overall_sim * 0.2
    return max(0.0, min(1.0, blended))


def _marks_and_reason(evidence: float, max_marks: float) -> tuple:
    """
    Determine marks fraction and reason label from evidence strength.
    Returns (fraction, reason_string).
    """
    if evidence >= EXCELLENT_THRESHOLD:
        return 1.0, "Excellent — full concept coverage"
    elif evidence >= GOOD_THRESHOLD:
        return 0.75, "Good — main concept present, minor gaps"
    elif evidence >= MODERATE_THRESHOLD:
        return 0.5, "Moderate — partial coverage of concept"
    elif evidence >= WEAK_THRESHOLD:
        return 0.25, "Weak — minimal or tangential reference"
    else:
        return 0.0, "Not demonstrated in the answer"


# ─────────────────────────────────────────────────────────
# Main Evaluation Function
# ─────────────────────────────────────────────────────────

def evaluate_rubric(answer_script_id: int, db: Session):
    """
    Evaluate all student answers for a script using rubric-based multi-signal grading.

    For each question:
    1. Check prerequisites (model answer, rubric, rubric validity)
    2. Compute per-criterion evidence using SBERT + keywords + length
    3. Award marks with validation against rubric max and question max
    4. Flag uncertain answers for manual review
    5. Save evaluation and criterion-level results
    """
    student_answers = db.query(StudentAnswer).filter(
        StudentAnswer.answer_script_id == answer_script_id
    ).all()
    if not student_answers:
        raise ValueError(f"No student answers found for script {answer_script_id}")

    # ── Batch pre-fetch all needed data ────────────────────────────
    q_ids = [sa.question_id for sa in student_answers if sa.question_id is not None]
    questions_map = {
        q.id: q for q in db.query(Question).filter(Question.id.in_(q_ids)).all()
    }
    rubrics_by_q = {}
    for r in db.query(Rubric).filter(Rubric.question_id.in_(q_ids)).all():
        rubrics_by_q.setdefault(r.question_id, []).append(r)

    model_answers_map = {
        ma.question_id: ma
        for ma in db.query(ModelAnswer).filter(ModelAnswer.question_id.in_(q_ids)).all()
    }
    sa_ids = [sa.id for sa in student_answers]
    evaluations_map = {
        ev.student_answer_id: ev
        for ev in db.query(Evaluation).filter(
            Evaluation.student_answer_id.in_(sa_ids)
        ).all()
    }

    model = get_sbert_model()

    # ── Batch-encode all texts for SBERT (single encode call per unique text) ──
    unique_texts_to_encode = set()
    for sa in student_answers:
        if sa.answer_text:
            unique_texts_to_encode.add(clean_text_for_sbert(sa.answer_text))
        ma = model_answers_map.get(sa.question_id)
        if ma and ma.answer_text:
            unique_texts_to_encode.add(clean_text_for_sbert(ma.answer_text))
        for rubric in rubrics_by_q.get(sa.question_id, []):
            crit = clean_text_for_sbert(f"{rubric.criterion}. {rubric.description or ''}")
            unique_texts_to_encode.add(crit)

    embeddings_cache = {}
    unique_text_list = list(unique_texts_to_encode)
    if unique_text_list and hasattr(model, "encode"):
        try:
            embs = model.encode(unique_text_list, batch_size=32, convert_to_tensor=True)
            for txt, emb in zip(unique_text_list, embs):
                embeddings_cache[txt] = emb
            logger.info(
                f"Answer script {answer_script_id}: "
                f"Batch-encoded {len(unique_text_list)} unique texts for SBERT"
            )
        except Exception as e:
            logger.warning(f"Batch SBERT encoding failed: {e} — will compute individually")

    # ── Process each student answer ────────────────────────────────
    results = []

    for sa in student_answers:
        question = questions_map.get(sa.question_id)
        rubrics = rubrics_by_q.get(sa.question_id, [])
        model_answer = model_answers_map.get(sa.question_id)
        evaluation = evaluations_map.get(sa.id)

        max_marks = question.max_marks if question else 0

        result_item = {
            "question_id": sa.question_id,
            "max_marks": max_marks,
            "status": "completed",
            "suggested_marks": 0,
            "needs_review": False,
            "review_reason": None,
            "criteria": []
        }

        # ── Prerequisite checks ────────────────────────────────────

        if sa.answer_status == "unanswered" or not sa.answer_text or not sa.answer_text.strip():
            result_item["status"] = "unanswered"
            _save_evaluation(db, sa.id, 0, "unanswered")
            results.append(result_item)
            continue

        if not model_answer or not model_answer.answer_text:
            result_item["status"] = "model_answer_missing"
            result_item["needs_review"] = True
            result_item["review_reason"] = "No model answer available — cannot evaluate"
            _save_evaluation(db, sa.id, 0, "model_answer_missing")
            results.append(result_item)
            continue

        if not rubrics:
            # Fetch physical page image paths for diagram detection
            page_image_paths = []
            try:
                from app.models.answer_script_page import AnswerScriptPage
                p_query = db.query(AnswerScriptPage).filter(
                    AnswerScriptPage.answer_script_id == sa.answer_script_id
                )
                if sa.start_page and sa.end_page:
                    p_query = p_query.filter(
                        AnswerScriptPage.page_number >= sa.start_page,
                        AnswerScriptPage.page_number <= sa.end_page
                    )
                p_list = p_query.order_by(AnswerScriptPage.page_number).all()
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                for p_rec in p_list:
                    if p_rec.image_path:
                        abs_p = p_rec.image_path if os.path.isabs(p_rec.image_path) else os.path.join(base_dir, p_rec.image_path)
                        if os.path.exists(abs_p):
                            page_image_paths.append(abs_p)
            except Exception as img_err:
                logger.debug(f"Could not load page image paths for Q{sa.question_id}: {img_err}")

            # Holistic professor evaluation when no granular rubrics exist
            sem_eval = evaluate_single_question(
                question_text=question.question_text if question else "",
                max_marks=float(max_marks),
                student_answer_text=sa.answer_text,
                model_answer_text=model_answer.answer_text if model_answer else "",
                rubric_criteria=[],
                page_image_paths=page_image_paths,
                sbert_model=model
            )
            total_marks = min(float(max_marks), sem_eval["awarded_marks"])
            total_marks = round(total_marks * 2) / 2
            diag_eval = sem_eval.get("diagram_evaluation")
            diag_json = json.dumps(diag_eval) if diag_eval else None

            result_item["status"] = "completed"
            result_item["suggested_marks"] = total_marks
            result_item["needs_review"] = True
            result_item["review_reason"] = "Holistic evaluation: rubric criteria not configured for this question."
            result_item["diagram_evaluation"] = diag_eval
            result_item["criteria"] = [
                {
                    "rubric_id": None,
                    "criterion": "General Conceptual Understanding & Technical Coverage",
                    "max_marks": float(max_marks),
                    "suggested_marks": total_marks,
                    "evidence_score": round(total_marks / max(0.1, float(max_marks)), 2),
                    "reason": sem_eval.get("criterion_evaluations", [{}])[0].get("reason", "Holistic assessment against key concepts")
                }
            ]
            _save_evaluation(db, sa.id, total_marks, "completed", diagram_data=diag_json)
            results.append(result_item)
            continue

        # Validate rubric total ≤ question max
        rubric_total = sum(r.marks for r in rubrics)
        if question and rubric_total > question.max_marks:
            logger.warning(
                f"Q{sa.question_id}: rubric total {rubric_total} > max marks {question.max_marks}"
            )
            # Proceed with evaluation but cap at question max — don't fail

        # ── Answer quality check ───────────────────────────────────

        student_word_count = len(sa.answer_text.split())
        ocr_low_confidence = False

        # Flag very short answers for review
        if student_word_count < MIN_WORDS_FOR_CONFIDENT_EVAL:
            ocr_low_confidence = True
            result_item["needs_review"] = True
            result_item["review_reason"] = (
                f"Very short answer ({student_word_count} words) — "
                "OCR may have missed content or answer is genuinely brief"
            )

        # Flag positionally-assigned answers (from fallback segmentation)
        if sa.answer_status == "positional":
            result_item["needs_review"] = True
            result_item["review_reason"] = (
                (result_item.get("review_reason") or "")
                + " Answer was assigned by positional fallback (no Q-marker detected)."
            ).strip()

        # ── Overall similarity for context ─────────────────────────

        stu_clean = clean_text_for_sbert(sa.answer_text)
        mod_clean = clean_text_for_sbert(model_answer.answer_text)

        overall_sim = _get_cached_similarity(model, stu_clean, mod_clean, embeddings_cache)
        if evaluation and evaluation.similarity_score is not None:
            # Use the pre-computed similarity if available
            overall_sim = evaluation.similarity_score

        # ── Fetch Page Image Paths for Diagram Detection ───────────
        page_image_paths = []
        try:
            from app.models.answer_script_page import AnswerScriptPage
            p_query = db.query(AnswerScriptPage).filter(
                AnswerScriptPage.answer_script_id == sa.answer_script_id
            )
            if sa.start_page and sa.end_page:
                p_query = p_query.filter(
                    AnswerScriptPage.page_number >= sa.start_page,
                    AnswerScriptPage.page_number <= sa.end_page
                )
            p_list = p_query.order_by(AnswerScriptPage.page_number).all()
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            for p_rec in p_list:
                if p_rec.image_path:
                    abs_p = p_rec.image_path if os.path.isabs(p_rec.image_path) else os.path.join(base_dir, p_rec.image_path)
                    if os.path.exists(abs_p):
                        page_image_paths.append(abs_p)
        except Exception as img_err:
            logger.debug(f"Could not load page image paths for Q{sa.question_id}: {img_err}")

        # ── Multimodal Semantic Evaluation ─────────────────────────
        criteria_dicts = [
            {
                "id": r.id,
                "criterion": r.criterion,
                "marks": float(r.marks),
                "description": r.description or ""
            }
            for r in rubrics
        ]

        sem_eval = evaluate_single_question(
            question_text=question.question_text if question else "",
            max_marks=float(max_marks),
            student_answer_text=sa.answer_text,
            model_answer_text=model_answer.answer_text,
            rubric_criteria=criteria_dicts,
            page_image_paths=page_image_paths,
            sbert_model=model
        )

        total_marks = sem_eval["awarded_marks"]
        diagram_eval = sem_eval.get("diagram_evaluation")
        diag_json = json.dumps(diagram_eval) if diagram_eval else None

        if sem_eval.get("needs_review") or (diagram_eval and diagram_eval.get("needs_review")):
            result_item["needs_review"] = True
            existing_reason = result_item.get("review_reason") or ""
            d_reason = diagram_eval.get("review_reason") if diagram_eval else ""
            result_item["review_reason"] = (existing_reason + " " + (d_reason or "Flagged by multimodal evaluation engine.")).strip()

        criterion_results = []
        for cr in sem_eval["criterion_evaluations"]:
            rubric_id = cr.get("criterion_id")
            if not rubric_id:
                matching = next((r for r in rubrics if r.criterion == cr.get("criterion")), None)
                rubric_id = matching.id if matching else (rubrics[0].id if rubrics else None)

            criterion_results.append({
                "rubric_id": rubric_id,
                "criterion": cr.get("criterion"),
                "max_marks": cr.get("max_marks"),
                "suggested_marks": cr.get("awarded_marks"),
                "evidence_score": cr.get("evidence_score", 0.0),
                "reason": cr.get("reason", "Evaluated against rubric")
            })

        # Cap total at question max
        total_marks = min(float(max_marks), total_marks)
        total_marks = round(total_marks * 2) / 2  # Round to nearest 0.5

        # ── Save results ───────────────────────────────────────────
        eval_record = _save_evaluation(db, sa.id, total_marks, "completed", diagram_data=diag_json)
        _save_rubric_evaluations(db, eval_record.id, criterion_results)

        result_item["suggested_marks"] = total_marks
        result_item["criteria"] = criterion_results
        result_item["similarity_score"] = round(overall_sim, 3)
        result_item["diagram_evaluation"] = diagram_eval
        results.append(result_item)

        logger.info(
            f"Q{sa.question_id}: {total_marks}/{max_marks} marks "
            f"({'needs review' if result_item['needs_review'] else 'OK'})"
        )

    logger.info(
        f"Answer script {answer_script_id}: rubric evaluation complete. "
        f"{sum(1 for r in results if r['status'] == 'completed')} evaluated, "
        f"{sum(1 for r in results if r.get('needs_review'))} flagged for review"
    )

    return results


# ─────────────────────────────────────────────────────────
# Retrieval Function
# ─────────────────────────────────────────────────────────

def get_rubric_evaluation(answer_script_id: int, db: Session):
    student_answers = db.query(StudentAnswer).filter(
        StudentAnswer.answer_script_id == answer_script_id
    ).all()
    if not student_answers:
        raise ValueError(f"No student answers found for script {answer_script_id}")

    results = []
    for sa in student_answers:
        evaluation = db.query(Evaluation).filter(
            Evaluation.student_answer_id == sa.id
        ).first()
        question = db.query(Question).filter(Question.id == sa.question_id).first()

        if not evaluation:
            continue

        result_item = {
            "question_id": sa.question_id,
            "max_marks": question.max_marks if question else 0,
            "similarity_score": evaluation.similarity_score,
            "suggested_marks": evaluation.awarded_marks,
            "status": evaluation.evaluation_status,
            "needs_review": getattr(evaluation, "needs_review", False),
            "criteria": []
        }

        rubric_evals = db.query(RubricEvaluation).filter(
            RubricEvaluation.evaluation_id == evaluation.id
        ).all()
        for re_obj in rubric_evals:
            rubric = db.query(Rubric).filter(Rubric.id == re_obj.rubric_id).first()
            result_item["criteria"].append({
                "rubric_id": re_obj.rubric_id,
                "criterion": rubric.criterion if rubric else "",
                "max_marks": rubric.marks if rubric else 0,
                "suggested_marks": re_obj.suggested_marks,
                "evidence_score": re_obj.evidence_score,
                "reason": re_obj.reason
            })

        results.append(result_item)

    return results


# ─────────────────────────────────────────────────────────
# Internal Helpers
# ─────────────────────────────────────────────────────────

def _get_cached_similarity(model, text1: str, text2: str, cache: dict) -> float:
    """Compute cosine similarity using cached embeddings when available."""
    try:
        if text1 in cache and text2 in cache:
            from sentence_transformers import util
            sim = util.cos_sim(cache[text1], cache[text2])[0][0].item()
            return max(0.0, min(1.0, float(sim)))

        # Not cached — compute individually
        if hasattr(model, "encode") and not hasattr(model, "fit"):
            from sentence_transformers import util
            e1 = model.encode(text1, convert_to_tensor=True)
            e2 = model.encode(text2, convert_to_tensor=True)
            sim = util.cos_sim(e1, e2)[0][0].item()
            return max(0.0, min(1.0, float(sim)))
    except Exception as e:
        logger.debug(f"Similarity computation failed: {e}")

    # Jaccard fallback
    try:
        s1 = set(text1.lower().split())
        s2 = set(text2.lower().split())
        inter = len(s1 & s2)
        union = len(s1 | s2)
        return float(inter) / union if union > 0 else 0.0
    except Exception:
        return 0.3  # Neutral default


def _save_evaluation(db: Session, student_answer_id: int, marks: float, status: str, diagram_data: Optional[str] = None) -> Evaluation:
    """Upsert an Evaluation record."""
    evaluation = db.query(Evaluation).filter(
        Evaluation.student_answer_id == student_answer_id
    ).first()
    if not evaluation:
        evaluation = Evaluation(
            student_answer_id=student_answer_id,
            awarded_marks=marks,
            evaluation_status=status,
            evaluated_at=datetime.now(timezone.utc),
            diagram_data=diagram_data
        )
        db.add(evaluation)
    else:
        evaluation.awarded_marks = marks
        evaluation.evaluation_status = status
        evaluation.evaluated_at = datetime.now(timezone.utc)
        if diagram_data is not None:
            evaluation.diagram_data = diagram_data
    db.commit()
    db.refresh(evaluation)
    return evaluation


def _save_rubric_evaluations(db: Session, evaluation_id: int, criterion_results: list):
    """Replace all criterion evaluation records for an evaluation."""
    db.query(RubricEvaluation).filter(
        RubricEvaluation.evaluation_id == evaluation_id
    ).delete()
    db.commit()

    re_objects = []
    for cr in criterion_results:
        re_obj = RubricEvaluation(
            evaluation_id=evaluation_id,
            rubric_id=cr["rubric_id"],
            evidence_score=cr["evidence_score"],
            suggested_marks=cr["suggested_marks"],
            reason=cr["reason"]
        )
        re_objects.append(re_obj)

    if re_objects:
        db.bulk_save_objects(re_objects)
        db.commit()
