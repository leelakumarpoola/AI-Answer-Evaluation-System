import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.answer_script import AnswerScript
from app.models.student_answer import StudentAnswer
from app.models.model_answer import ModelAnswer
from app.models.evaluation import Evaluation

# Global model cache to avoid reloading
_sbert_model = None
MODEL_NAME = "all-MiniLM-L6-v2"

def get_sbert_model():
    global _sbert_model
    if _sbert_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sbert_model = SentenceTransformer(MODEL_NAME)
        except ImportError:
            print("WARNING: sentence-transformers not installed. Using fallback mock model for semantic similarity.")
            class MockModel:
                def encode(self, text, convert_to_tensor=False):
                    return text
            _sbert_model = MockModel()
    return _sbert_model

def clean_text_for_sbert(text: str) -> str:
    if not text:
        return ""
    # Collapse repeated whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def calculate_semantic_similarity(answer_script_id: int, db: Session):
    script = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    student_answers = db.query(StudentAnswer).filter(
        StudentAnswer.answer_script_id == answer_script_id
    ).all()
    
    if not student_answers:
        raise HTTPException(status_code=400, detail="No extracted student answers found for this script")
        
    model = get_sbert_model()
    
    results = []
    
    for sa in student_answers:
        question_id = sa.question_id
        
        # Check if model answer exists
        model_answer = db.query(ModelAnswer).filter(ModelAnswer.question_id == question_id).first()
        
        sim_score = None
        eval_status = ""
        
        if not model_answer or not model_answer.answer_text:
            eval_status = "model_answer_missing"
        elif sa.answer_status in ["unanswered", "not_evaluated"]:
            eval_status = "unanswered"
        elif not sa.answer_text or len(sa.answer_text.strip()) == 0:
            eval_status = "empty_student_answer"
        else:
            # We have valid text for both
            student_text = clean_text_for_sbert(sa.answer_text)
            model_text = clean_text_for_sbert(model_answer.answer_text)
            
            if len(student_text) > 0 and len(model_text) > 0:
                try:
                    # Calculate similarity
                    if hasattr(model, 'encode') and not hasattr(model, 'fit'):
                        # This is a real model or mock
                        try:
                            from sentence_transformers import util
                            emb1 = model.encode(student_text, convert_to_tensor=True)
                            emb2 = model.encode(model_text, convert_to_tensor=True)
                            cosine_scores = util.cos_sim(emb1, emb2)
                            sim_score = cosine_scores[0][0].item()
                        except ImportError:
                            # Fallback dummy similarity for mock
                            # Very basic jaccard similarity for mock testing
                            set1 = set(student_text.lower().split())
                            set2 = set(model_text.lower().split())
                            intersection = len(set1.intersection(set2))
                            union = len(set1.union(set2))
                            sim_score = float(intersection) / union if union > 0 else 0.0
                    else:
                        sim_score = 0.5
                        
                    # Normalize to 0.0 - 1.0 safely
                    sim_score = max(0.0, min(1.0, float(sim_score)))
                    eval_status = "similarity_calculated"
                except Exception as e:
                    print(f"SBERT Encoding error: {e}")
                    eval_status = "embedding_failed"
            else:
                eval_status = "insufficient_text"
                
        # Store in Evaluation
        evaluation = db.query(Evaluation).filter(Evaluation.student_answer_id == sa.id).first()
        
        if not evaluation:
            evaluation = Evaluation(
                student_answer_id=sa.id,
                similarity_score=sim_score,
                evaluation_status=eval_status,
                evaluated_at=datetime.now(timezone.utc)
            )
            db.add(evaluation)
        else:
            evaluation.similarity_score = sim_score
            evaluation.evaluation_status = eval_status
            evaluation.evaluated_at = datetime.now(timezone.utc)
            
        db.commit()
        db.refresh(evaluation)
        
        results.append({
            "question_id": question_id,
            "similarity_score": sim_score,
            "status": eval_status
        })
        
    return {
        "answer_script_id": answer_script_id,
        "status": "completed",
        "results": results
    }

def get_similarity_results(answer_script_id: int, db: Session):
    script = db.query(AnswerScript).filter(AnswerScript.id == answer_script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Answer script not found")
        
    student_answers = db.query(StudentAnswer).filter(
        StudentAnswer.answer_script_id == answer_script_id
    ).all()
    
    results = []
    for sa in student_answers:
        evaluation = db.query(Evaluation).filter(Evaluation.student_answer_id == sa.id).first()
        if evaluation:
            results.append({
                "question_id": sa.question_id,
                "similarity_score": evaluation.similarity_score,
                "status": evaluation.evaluation_status
            })
            
    return {
        "answer_script_id": answer_script_id,
        "results": results
    }
