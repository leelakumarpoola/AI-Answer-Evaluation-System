import requests
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.professor import Professor
from app.models.student import Student
from app.models.exam import Exam
from app.models.answer_script import AnswerScript
from app.models.question import Question
from app.models.model_answer import ModelAnswer
from app.models.rubric import Rubric
from app.models.student_answer import StudentAnswer
from app.models.evaluation import Evaluation
from app.models.rubric_evaluation import RubricEvaluation
from app.utils.security import get_password_hash

BASE_URL = "http://127.0.0.1:8001"

def login(email, password, role="professor"):
    if role == "professor":
        json_data = {"email": email, "password": password}
    else:
        json_data = {"identifier": email, "password": password}
        
    r = requests.post(f"{BASE_URL}/auth/{role}/login", json=json_data)
    if r.status_code == 200:
        token = r.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    return None

def setup_data():
    db = SessionLocal()
    
    # Prof A & B
    prof_a = db.query(Professor).filter(Professor.email == "profa15@vit.ac.in").first()
    if not prof_a:
        prof_a = Professor(name="Prof A", email="profa15@vit.ac.in", department="CSE", password_hash=get_password_hash("password123"))
        db.add(prof_a)
        
    prof_b = db.query(Professor).filter(Professor.email == "profb15@vit.ac.in").first()
    if not prof_b:
        prof_b = Professor(name="Prof B", email="profb15@vit.ac.in", department="CSE", password_hash=get_password_hash("password123"))
        db.add(prof_b)
        
    # Stud A & B
    stud_a = db.query(Student).filter(Student.email == "studa15@vit.ac.in").first()
    if not stud_a:
        stud_a = Student(name="Student A", roll_number="23BCE9915", email="studa15@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_a)
        
    stud_b = db.query(Student).filter(Student.email == "studb15@vit.ac.in").first()
    if not stud_b:
        stud_b = Student(name="Student B", roll_number="23BCE9916", email="studb15@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_b)
        
    db.commit()
    
    # Exam for Prof A
    exam_a = db.query(Exam).filter(Exam.professor_id == prof_a.id, Exam.subject_id == 1).first()
    if not exam_a:
        exam_a = Exam(subject_id=1, professor_id=prof_a.id, name="Phase 15 Test", total_marks=100)
        db.add(exam_a)
        db.commit()
        
    # Script A for Stud A
    script_a = db.query(AnswerScript).filter(AnswerScript.exam_id == exam_a.id, AnswerScript.student_id == stud_a.id).first()
    if not script_a:
        script_a = AnswerScript(exam_id=exam_a.id, student_id=stud_a.id, file_path="dummy")
        db.add(script_a)
        db.commit()
        
    # Question
    q = db.query(Question).filter(Question.exam_id == exam_a.id).first()
    if not q:
        q = Question(exam_id=exam_a.id, question_number=1, question_text="What is Blockchain?", max_marks=10)
        db.add(q)
        db.commit()
        
    # Rubric
    r_def = db.query(Rubric).filter(Rubric.question_id == q.id, Rubric.criterion == "Definition").first()
    if not r_def:
        r_def = Rubric(question_id=q.id, criterion="Definition", marks=5)
        db.add(r_def)
        
    r_ex = db.query(Rubric).filter(Rubric.question_id == q.id, Rubric.criterion == "Example").first()
    if not r_ex:
        r_ex = Rubric(question_id=q.id, criterion="Example", marks=5)
        db.add(r_ex)
    db.commit()
        
    # Student Answer
    sa = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == script_a.id, StudentAnswer.question_id == q.id).first()
    if not sa:
        sa = StudentAnswer(answer_script_id=script_a.id, question_id=q.id, answer_text="It is a distributed ledger.")
        db.add(sa)
        db.commit()
        
    # Evaluation
    ev = db.query(Evaluation).filter(Evaluation.student_answer_id == sa.id).first()
    if not ev:
        ev = Evaluation(student_answer_id=sa.id, awarded_marks=0, max_marks=10, similarity_score=0.5, evaluation_status="completed")
        db.add(ev)
        db.commit()
        
        # Rubric Eval
        re1 = RubricEvaluation(evaluation_id=ev.id, rubric_id=r_def.id, evidence_score=0.9, suggested_marks=4.5, reason="Good definition")
        re2 = RubricEvaluation(evaluation_id=ev.id, rubric_id=r_ex.id, evidence_score=0.0, suggested_marks=0, reason="No example provided")
        db.add(re1)
        db.add(re2)
        db.commit()
        
    ids = {
        "prof_a_id": prof_a.id,
        "prof_b_id": prof_b.id,
        "stud_a_id": stud_a.id,
        "stud_b_id": stud_b.id,
        "script_a_id": script_a.id,
        "eval_id": ev.id
    }
    db.close()
    return ids

def run_tests():
    ids = setup_data()
    
    print("TEST 1 Professor login.")
    prof_a_headers = login("profa15@vit.ac.in", "password123", "professor")
    prof_b_headers = login("profb15@vit.ac.in", "password123", "professor")
    assert prof_a_headers is not None
    print("PASS")
    
    print("TEST 2 Student login.")
    stud_a_headers = login("studa15@vit.ac.in", "password123", "student")
    stud_b_headers = login("studb15@vit.ac.in", "password123", "student")
    assert stud_a_headers is not None
    print("PASS")
    
    print("TEST 3 Unauthenticated feedback generation.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{ids['script_a_id']}/feedback")
    assert r.status_code == 401
    print("PASS")
    
    print("TEST 4 Student attempts feedback generation.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{ids['script_a_id']}/feedback", headers=stud_a_headers)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 5 Professor generates feedback for own exam.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{ids['script_a_id']}/feedback", headers=prof_a_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data["feedback"]) == 1
    text = data["feedback"][0]["feedback_text"]
    assert "correctly addresses" in text
    assert "Definition" in text
    assert "missing or weak" in text
    assert "Example" in text
    print("PASS")
    
    print("TEST 6 Professor attempts feedback generation for another professor's exam.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{ids['script_a_id']}/feedback", headers=prof_b_headers)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 7 Student retrieves own feedback.")
    r = requests.get(f"{BASE_URL}/answer-scripts/{ids['script_a_id']}/feedback", headers=stud_a_headers)
    assert r.status_code == 200
    print("PASS")
    
    print("TEST 8 Student attempts to retrieve another student's feedback.")
    r = requests.get(f"{BASE_URL}/answer-scripts/{ids['script_a_id']}/feedback", headers=stud_b_headers)
    assert r.status_code == 403
    print("PASS")

if __name__ == "__main__":
    run_tests()
