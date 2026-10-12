from sqlalchemy.orm import Session
from app.models.student_answer import StudentAnswer
from app.models.rubric import Rubric
from app.models.evaluation import Evaluation
from app.models.question import Question
from app.models.model_answer import ModelAnswer
from app.models.rubric_evaluation import RubricEvaluation
from app.services.semantic_similarity_service import get_sbert_model, clean_text_for_sbert
from datetime import datetime, timezone
import math

def evaluate_rubric(answer_script_id: int, db: Session):
    student_answers = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == answer_script_id).all()
    if not student_answers:
        raise ValueError(f"No student answers found for script {answer_script_id}")

    results = []
    
    for sa in student_answers:
        question = db.query(Question).filter(Question.id == sa.question_id).first()
        rubrics = db.query(Rubric).filter(Rubric.question_id == sa.question_id).all()
        model_answer = db.query(ModelAnswer).filter(ModelAnswer.question_id == sa.question_id).first()
        evaluation = db.query(Evaluation).filter(Evaluation.student_answer_id == sa.id).first()
        
        result_item = {
            "question_id": sa.question_id,
            "max_marks": question.max_marks if question else 0,
            "status": "completed",
            "suggested_marks": 0,
            "criteria": []
        }

        # Step 12: Unanswered question
        if sa.answer_status == "unanswered" or not sa.answer_text or sa.answer_text.strip() == "":
            result_item["status"] = "unanswered"
            _save_evaluation(db, sa.id, 0, result_item["status"])
            results.append(result_item)
            continue
            
        # Step 13: Missing model answer
        if not model_answer:
            result_item["status"] = "model_answer_missing"
            _save_evaluation(db, sa.id, 0, result_item["status"])
            results.append(result_item)
            continue
            
        # Step 14: Missing rubric
        if not rubrics or len(rubrics) == 0:
            result_item["status"] = "rubric_missing"
            _save_evaluation(db, sa.id, 0, result_item["status"])
            results.append(result_item)
            continue

        # Step 15: Validating rubric
        rubric_total = sum([r.marks for r in rubrics])
        if rubric_total > question.max_marks:
            result_item["status"] = "invalid_rubric"
            _save_evaluation(db, sa.id, 0, result_item["status"])
            results.append(result_item)
            continue

        # Prepare for calculation
        model = get_sbert_model()
        student_text_clean = clean_text_for_sbert(sa.answer_text)
        overall_sim = evaluation.similarity_score if evaluation and evaluation.similarity_score is not None else 0.5
        
        total_suggested_marks = 0
        criterion_results = []
        
        for rubric in rubrics:
            # Step A: Representation
            crit_text = f"{rubric.criterion}. {rubric.description or ''}"
            crit_text_clean = clean_text_for_sbert(crit_text)
            
            # Step B & C: SBERT Evidence similarity
            sim_score = _calculate_similarity(model, student_text_clean, crit_text_clean)
            
            # Use overall similarity as a modifier or just blend it
            evidence_strength = (sim_score * 0.7) + (overall_sim * 0.3)
            
            # Step D: Map evidence strength to a fraction
            if evidence_strength >= 0.75:
                fraction = 1.0
                reason = "Very strong evidence"
            elif evidence_strength >= 0.6:
                fraction = 0.75
                reason = "Strong evidence"
            elif evidence_strength >= 0.4:
                fraction = 0.5
                reason = "Moderate evidence"
            elif evidence_strength >= 0.2:
                fraction = 0.25
                reason = "Weak/partial evidence"
            else:
                fraction = 0.0
                reason = "No relevant evidence"
            
            # Calculate marks for this criterion
            suggested_marks = fraction * rubric.marks
            # Ensure boundaries
            suggested_marks = max(0.0, min(rubric.marks, suggested_marks))
            # Rounding to 0.5 granularity
            suggested_marks = round(suggested_marks * 2) / 2
            
            total_suggested_marks += suggested_marks
            
            crit_res = {
                "rubric_id": rubric.id,
                "criterion": rubric.criterion,
                "max_marks": rubric.marks,
                "suggested_marks": suggested_marks,
                "evidence_score": float(evidence_strength),
                "reason": reason
            }
            criterion_results.append(crit_res)
        
        # Ensure overall total is bounded
        total_suggested_marks = max(0.0, min(question.max_marks, total_suggested_marks))
        
        # Save results
        eval_record = _save_evaluation(db, sa.id, total_suggested_marks, "rubric_evaluated")
        
        # Save rubric evaluation details
        _save_rubric_evaluations(db, eval_record.id, criterion_results)
        
        result_item["suggested_marks"] = total_suggested_marks
        result_item["criteria"] = criterion_results
        result_item["similarity_score"] = overall_sim
        results.append(result_item)
        
    return results

def get_rubric_evaluation(answer_script_id: int, db: Session):
    student_answers = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == answer_script_id).all()
    if not student_answers:
        raise ValueError(f"No student answers found for script {answer_script_id}")
        
    results = []
    for sa in student_answers:
        evaluation = db.query(Evaluation).filter(Evaluation.student_answer_id == sa.id).first()
        question = db.query(Question).filter(Question.id == sa.question_id).first()
        
        if not evaluation:
            continue
            
        result_item = {
            "question_id": sa.question_id,
            "max_marks": question.max_marks if question else 0,
            "similarity_score": evaluation.similarity_score,
            "suggested_marks": evaluation.awarded_marks,
            "status": evaluation.evaluation_status,
            "criteria": []
        }
        
        rubric_evals = db.query(RubricEvaluation).filter(RubricEvaluation.evaluation_id == evaluation.id).all()
        for re in rubric_evals:
            rubric = db.query(Rubric).filter(Rubric.id == re.rubric_id).first()
            result_item["criteria"].append({
                "rubric_id": re.rubric_id,
                "criterion": rubric.criterion if rubric else "",
                "max_marks": rubric.marks if rubric else 0,
                "suggested_marks": re.suggested_marks,
                "evidence_score": re.evidence_score,
                "reason": re.reason
            })
            
        results.append(result_item)
        
    return results

def _calculate_similarity(model, text1: str, text2: str) -> float:
    try:
        if hasattr(model, 'encode') and not hasattr(model, 'fit'):
            try:
                from sentence_transformers import util
                emb1 = model.encode(text1, convert_to_tensor=True)
                emb2 = model.encode(text2, convert_to_tensor=True)
                cosine_scores = util.cos_sim(emb1, emb2)
                sim = cosine_scores[0][0].item()
            except ImportError:
                # Mock similarity fallback
                set1 = set(text1.lower().split())
                set2 = set(text2.lower().split())
                intersection = len(set1.intersection(set2))
                union = len(set1.union(set2))
                sim = float(intersection) / union if union > 0 else 0.0
            return max(0.0, min(1.0, float(sim)))
    except Exception:
        pass
    return 0.5

def _save_evaluation(db: Session, student_answer_id: int, marks: float, status: str):
    evaluation = db.query(Evaluation).filter(Evaluation.student_answer_id == student_answer_id).first()
    if not evaluation:
        evaluation = Evaluation(
            student_answer_id=student_answer_id,
            awarded_marks=marks,
            evaluation_status=status,
            evaluated_at=datetime.now(timezone.utc)
        )
        db.add(evaluation)
    else:
        evaluation.awarded_marks = marks
        evaluation.evaluation_status = status
        evaluation.evaluated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(evaluation)
    return evaluation

def _save_rubric_evaluations(db: Session, evaluation_id: int, criterion_results: list):
    # Idempotent approach: Delete existing for this evaluation_id
    db.query(RubricEvaluation).filter(RubricEvaluation.evaluation_id == evaluation_id).delete()
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
