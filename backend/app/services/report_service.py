import statistics
from sqlalchemy.orm import Session
from app.models.exam import Exam
from app.models.student import Student
from app.models.answer_script import AnswerScript
from app.models.question import Question
from app.models.student_answer import StudentAnswer
from app.models.evaluation import Evaluation
from app.services.result_service import generate_student_exam_result

def get_performance_category(percentage: float) -> str:
    if percentage >= 75:
        return "HIGH_PERFORMANCE"
    elif percentage >= 50:
        return "MEDIUM_PERFORMANCE"
    return "LOW_PERFORMANCE"

def generate_exam_summary(db: Session, exam_id: int):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return None
        
    students = db.query(Student).all()
    scripts = db.query(AnswerScript).filter(AnswerScript.exam_id == exam_id).all()
    
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    maximum_marks = sum(q.max_marks for q in questions if q.max_marks)
    
    total_students = len(students)
    scripts_by_student = {s.student_id: s for s in scripts}
    
    students_completed = 0
    students_pending = 0
    
    completed_marks = []
    
    for student in students:
        res = generate_student_exam_result(db, exam_id, student.id)
        if res and res["status"] == "COMPLETED":
            students_completed += 1
            completed_marks.append(res["total_marks"])
        elif res and res["status"] == "PENDING_REVIEW":
            students_pending += 1
            
    # Evaluations total
    all_answers = []
    for script in scripts:
        ans = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == script.id).all()
        all_answers.extend(ans)
        
    total_evals = 0
    approved_evals = 0
    pending_evals = 0
    
    for ans in all_answers:
        if ans.evaluation:
            total_evals += 1
            if ans.evaluation.review_status == "approved":
                approved_evals += 1
            else:
                pending_evals += 1
                
    avg = None
    high = None
    low = None
    med = None
    avg_pct = None
    
    if completed_marks:
        avg = round(sum(completed_marks) / len(completed_marks), 2)
        high = max(completed_marks)
        low = min(completed_marks)
        med = round(statistics.median(completed_marks), 2)
        if maximum_marks > 0:
            avg_pct = round((avg / maximum_marks) * 100, 2)
            
    return {
        "exam_id": exam.id,
        "exam_name": exam.name,
        "subject_name": exam.subject.name,
        "course_code": exam.subject.code,
        "exam_date": exam.exam_date,
        "maximum_marks": maximum_marks,
        "total_students": total_students,
        "students_with_answer_scripts": len(scripts),
        "students_completed": students_completed,
        "students_pending": students_pending,
        "total_evaluations": total_evals,
        "approved_evaluations": approved_evals,
        "pending_evaluations": pending_evals,
        "average_marks": avg,
        "highest_marks": high,
        "lowest_marks": low,
        "median_marks": med,
        "average_percentage": avg_pct
    }

def get_student_performance(db: Session, exam_id: int):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return None
        
    students = db.query(Student).order_by(Student.roll_number).all()
    scripts = {
        s.student_id: s
        for s in db.query(AnswerScript).filter(AnswerScript.exam_id == exam_id).all()
    }

    results = []
    for student in students:
        script = scripts.get(student.id)
        res = generate_student_exam_result(db, exam_id, student.id)
        if not res:
            continue

        stage = "not_submitted"
        ai_marks = 0.0

        if script:
            answers = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == script.id).all()
            evals = [a.evaluation for a in answers if a.evaluation]
            if evals:
                ai_marks = sum((e.awarded_marks or 0.0) for e in evals)
                all_approved = all(e.review_status == "approved" and e.final_marks is not None for e in evals)
                stage = "approved" if all_approved else "ai_evaluated"
            else:
                stage = "script_uploaded"

        results.append({
            "student_id": student.id,
            "student_name": student.name,
            "roll_number": student.roll_number,
            "email": student.email,
            "total_marks": res["total_marks"],
            "maximum_marks": res["maximum_marks"],
            "percentage": res["percentage"],
            "result_status": res["status"],
            "ai_suggested_marks": round(ai_marks, 2) if ai_marks else (res["total_marks"] if stage == "approved" else None),
            "answer_script_id": script.id if script else None,
            "evaluation_stage": stage
        })
    return results

def get_question_performance(db: Session, exam_id: int):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return None
        
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    results = []
    
    for q in questions:
        q_max = q.max_marks or 0.0
        
        # Get all approved evaluations for this question
        answers = db.query(StudentAnswer).filter(StudentAnswer.question_id == q.id).all()
        approved_marks = []
        
        for ans in answers:
            if ans.evaluation and ans.evaluation.review_status == "approved" and ans.evaluation.final_marks is not None:
                approved_marks.append(ans.evaluation.final_marks)
                
        if approved_marks:
            avg = round(sum(approved_marks) / len(approved_marks), 2)
            high = max(approved_marks)
            low = min(approved_marks)
            pct = round((avg / q_max) * 100, 2) if q_max > 0 else 0.0
            cat = get_performance_category(pct)
        else:
            avg = None
            high = None
            low = None
            pct = None
            cat = None
            
        results.append({
            "question_number": str(q.question_number),
            "question_text": q.question_text,
            "maximum_marks": q_max,
            "students_evaluated": len(approved_marks),
            "average_marks": avg,
            "highest_marks": high,
            "lowest_marks": low,
            "average_percentage": pct,
            "performance_category": cat
        })
        
    return results

def get_marks_distribution(db: Session, exam_id: int):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return None
        
    students = db.query(Student).all()
    
    distribution = {
        "0-39": 0,
        "40-49": 0,
        "50-59": 0,
        "60-69": 0,
        "70-79": 0,
        "80-89": 0,
        "90-100": 0
    }
    
    for student in students:
        res = generate_student_exam_result(db, exam_id, student.id)
        if res and res["status"] == "COMPLETED":
            pct = res["percentage"]
            if pct < 40:
                distribution["0-39"] += 1
            elif pct < 50:
                distribution["40-49"] += 1
            elif pct < 60:
                distribution["50-59"] += 1
            elif pct < 70:
                distribution["60-69"] += 1
            elif pct < 80:
                distribution["70-79"] += 1
            elif pct < 90:
                distribution["80-89"] += 1
            else:
                distribution["90-100"] += 1
                
    return {"distribution": distribution}

def get_completion_report(db: Session, exam_id: int):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return None
        
    students = db.query(Student).all()
    total_students = len(students)
    
    scripts = db.query(AnswerScript).filter(AnswerScript.exam_id == exam_id).all()
    scripts_uploaded = len(scripts)
    
    scripts_processed = len(scripts) # Placeholder
    
    students_with_extracted = 0
    students_completed = 0
    students_pending = 0
    
    for student in students:
        res = generate_student_exam_result(db, exam_id, student.id)
        if res:
            if res["status"] == "COMPLETED":
                students_completed += 1
                students_with_extracted += 1
            elif res["status"] == "PENDING_REVIEW":
                students_pending += 1
                students_with_extracted += 1
                
    return {
        "total_students": total_students,
        "answer_scripts_uploaded": scripts_uploaded,
        "answer_scripts_processed": scripts_uploaded, # As everything is processed immediately in this mockup structure mostly
        "students_with_extracted_answers": students_with_extracted,
        "students_with_approved_results": students_completed,
        "students_pending_review": students_pending
    }
