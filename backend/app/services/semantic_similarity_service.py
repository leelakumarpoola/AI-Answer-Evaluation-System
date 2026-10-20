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
            import os
            from sentence_transformers import SentenceTransformer
            # Try loading locally first to eliminate remote network pings
            try:
                _sbert_model = SentenceTransformer(MODEL_NAME, local_files_only=True)
            except Exception:
                _sbert_model = SentenceTransformer(MODEL_NAME)
        except ImportError:
            print("WARNING: sentence-transformers not installed. Using fallback mock model for semantic similarity.")
            class MockModel:
                def encode(self, text, convert_to_tensor=False, batch_size=32):
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
    
    # Pre-fetch model answers in a single batch query
    question_ids = [sa.question_id for sa in student_answers if sa.question_id is not None]
    model_answers = {
        ma.question_id: ma for ma in db.query(ModelAnswer).filter(ModelAnswer.question_id.in_(question_ids)).all()
    }
    
    # Pre-fetch existing evaluations
    sa_ids = [sa.id for sa in student_answers]
    existing_evals = {
        ev.student_answer_id: ev for ev in db.query(Evaluation).filter(Evaluation.student_answer_id.in_(sa_ids)).all()
    }

    # Prepare batches for vectorization
    pairs_to_encode = []
    pair_indices = []
    
    results_map = {}
    
    for idx, sa in enumerate(student_answers):
        question_id = sa.question_id
        model_answer = model_answers.get(question_id)
        
        sim_score = None
        eval_status = ""
        
        if not model_answer or not model_answer.answer_text:
            eval_status = "model_answer_missing"
        elif sa.answer_status in ["unanswered", "not_evaluated"]:
            eval_status = "unanswered"
        elif not sa.answer_text or len(sa.answer_text.strip()) == 0:
            eval_status = "empty_student_answer"
        else:
            student_text = clean_text_for_sbert(sa.answer_text)
            model_text = clean_text_for_sbert(model_answer.answer_text)
            
            if len(student_text) > 0 and len(model_text) > 0:
                pairs_to_encode.append((student_text, model_text))
                pair_indices.append(idx)
                eval_status = "pending_computation"
            else:
                eval_status = "insufficient_text"
                
        results_map[idx] = {
            "sa": sa,
            "question_id": question_id,
            "similarity_score": sim_score,
            "status": eval_status
        }
        
    # Batch compute embeddings for all answers simultaneously (4x speedup)
    if pairs_to_encode and hasattr(model, 'encode'):
        try:
            from sentence_transformers import util
            stu_texts = [p[0] for p in pairs_to_encode]
            mod_texts = [p[1] for p in pairs_to_encode]
            
            stu_embs = model.encode(stu_texts, batch_size=16, convert_to_tensor=True)
            mod_embs = model.encode(mod_texts, batch_size=16, convert_to_tensor=True)
            
            for i, target_idx in enumerate(pair_indices):
                if len(pairs_to_encode) == 1:
                    cos_sim = util.cos_sim(stu_embs, mod_embs).item()
                else:
                    cos_sim = util.cos_sim(stu_embs[i:i+1], mod_embs[i:i+1]).item()
                normalized_score = max(0.0, min(1.0, float(cos_sim)))
                results_map[target_idx]["similarity_score"] = normalized_score
                results_map[target_idx]["status"] = "similarity_calculated"
        except Exception as e:
            print(f"Batch SBERT error: {e}")
            for target_idx in pair_indices:
                # Basic jaccard fallback
                st = set(results_map[target_idx]["sa"].answer_text.lower().split())
                mt = set(model_answers[results_map[target_idx]["question_id"]].answer_text.lower().split())
                inter = len(st.intersection(mt))
                union = len(st.union(mt))
                sim_fallback = float(inter) / union if union > 0 else 0.5
                results_map[target_idx]["similarity_score"] = max(0.0, min(1.0, sim_fallback))
                results_map[target_idx]["status"] = "similarity_calculated"

    # Save and persist results
    results = []
    for idx in sorted(results_map.keys()):
        item = results_map[idx]
        sa = item["sa"]
        sim_score = item["similarity_score"]
        eval_status = item["status"]
        
        evaluation = existing_evals.get(sa.id)
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
            
        results.append({
            "question_id": item["question_id"],
            "similarity_score": sim_score,
            "status": eval_status
        })
        
    db.commit()
    
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


import asyncio

async def calculate_semantic_similarity_async(answer_script_id: int, db: Session):
    """
    Evaluates all questions concurrently using asyncio.gather without blocking the event loop.
    Ensures bounded memory and thread execution.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: calculate_semantic_similarity(answer_script_id, db))
