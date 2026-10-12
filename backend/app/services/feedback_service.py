from sqlalchemy.orm import Session
from app.models.evaluation import Evaluation
from app.models.feedback import Feedback
from app.models.rubric_evaluation import RubricEvaluation

def generate_feedback_text(evaluation: Evaluation) -> str:
    """
    Generates evidence-grounded textual feedback based on the Phase 14 evaluation data.
    Ensures 100% grounding, avoiding any hallucinations.
    """
    if evaluation.evaluation_status == "unanswered":
        return "No answer was detected for this question. Review the relevant concepts and provide a complete response addressing each rubric criterion."
    
    if evaluation.evaluation_status == "missing_model_answer":
        return "Detailed feedback cannot be provided because the reference model answer is unavailable."
        
    if evaluation.evaluation_status == "missing_rubric":
        return "Detailed rubric-based feedback could not be generated because the evaluation rubric is unavailable."
        
    if evaluation.evaluation_status != "completed":
        return f"Evaluation failed ({evaluation.evaluation_status}), unable to generate feedback."

    strengths = []
    weaknesses = []
    improvements = []
    
    for crit_eval in evaluation.criterion_evaluations:
        rubric_text = crit_eval.rubric.criterion
        score = crit_eval.evidence_score
        
        if score >= 0.8:
            strengths.append(rubric_text)
        elif score > 0.0:
            weaknesses.append(f"{rubric_text} (partially addressed)")
            improvements.append(f"expand on {rubric_text.lower()}")
        else:
            weaknesses.append(rubric_text)
            improvements.append(f"include details regarding {rubric_text.lower()}")
            
    feedback_lines = []
    if strengths:
        feedback_lines.append(f"Your answer correctly addresses the following concepts: {', '.join(strengths)}.")
    
    if weaknesses:
        feedback_lines.append(f"However, the response is missing or weak in these areas: {', '.join(weaknesses)}.")
        
    if improvements:
        feedback_lines.append(f"To improve, ensure you {', and '.join(improvements[:2])}.")
        
    if not strengths and not weaknesses:
        return "Insufficient answer content was detected to provide detailed feedback."
        
    return " ".join(feedback_lines)

def generate_and_store_feedback(db: Session, evaluation: Evaluation) -> Feedback:
    """
    Generates feedback and stores it in the database.
    Updates the existing feedback record if it already exists (Idempotency).
    """
    text = generate_feedback_text(evaluation)
    
    # Check for existing feedback
    existing_feedback = db.query(Feedback).filter(Feedback.evaluation_id == evaluation.id).first()
    
    if existing_feedback:
        existing_feedback.feedback_text = text
        db.commit()
        db.refresh(existing_feedback)
        return existing_feedback
    else:
        new_feedback = Feedback(
            evaluation_id=evaluation.id,
            feedback_text=text
        )
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
        return new_feedback
