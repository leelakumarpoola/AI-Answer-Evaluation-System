from sqlalchemy.orm import Session
from app.models.student import Student
from app.models.exam import Exam
from app.models.question import Question
from app.models.answer_script import AnswerScript
from app.models.student_answer import StudentAnswer
from app.models.evaluation import Evaluation

def generate_student_exam_result(db: Session, exam_id: int, student_id: int):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        return None
        
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        return None
        
    script = db.query(AnswerScript).filter(AnswerScript.exam_id == exam_id, AnswerScript.student_id == student_id).first()
    
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    total_maximum_marks = sum(q.max_marks for q in questions if q.max_marks)
    
    if not script:
        return {
            "student_name": student.name,
            "roll_number": student.roll_number,
            "subject": exam.subject.name,
            "course_code": exam.subject.code,
            "exam_name": exam.name,
            "exam_date": exam.exam_date,
            "total_marks": 0.0,
            "maximum_marks": total_maximum_marks,
            "percentage": 0.0,
            "status": "NOT_SUBMITTED",
            "questions": []
        }
        
    student_answers = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == script.id).all()
    sa_by_q = {sa.question_id: sa for sa in student_answers}
    
    question_results = []
    total_final_marks = 0.0
    all_completed = True
    
    for q in questions:
        q_max = q.max_marks or 0.0
        sa = sa_by_q.get(q.id)
        
        q_res = {
            "question_number": str(q.question_number),
            "question_text": q.question_text,
            "maximum_marks": q_max,
            "ai_suggested_marks": None,
            "final_marks": None,
            "professor_remarks": None,
            "ai_feedback": None,
            "review_status": "missing"
        }
        
        if sa and sa.evaluation:
            ev = sa.evaluation
            q_res["ai_suggested_marks"] = ev.awarded_marks
            q_res["review_status"] = ev.review_status
            if ev.review_status == "approved":
                fm = ev.final_marks or 0.0
                q_res["final_marks"] = fm
                total_final_marks += fm
            else:
                all_completed = False
            
            q_res["professor_remarks"] = ev.professor_remarks
            
            if ev.feedback and len(ev.feedback) > 0:
                q_res["ai_feedback"] = ev.feedback[-1].feedback_text
        else:
            all_completed = False
            
        question_results.append(q_res)
        
    status = "COMPLETED" if all_completed else "PENDING_REVIEW"
    
    percentage = 0.0
    if total_maximum_marks > 0:
        percentage = round((total_final_marks / total_maximum_marks) * 100, 2)
        
    return {
        "student_name": student.name,
        "roll_number": student.roll_number,
        "subject": exam.subject.name,
        "course_code": exam.subject.code,
        "exam_name": exam.name,
        "exam_date": exam.exam_date,
        "total_marks": total_final_marks,
        "maximum_marks": total_maximum_marks,
        "percentage": percentage,
        "status": status,
        "questions": question_results
    }
