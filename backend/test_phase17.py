import requests
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.professor import Professor
from app.models.student import Student
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.answer_script import AnswerScript
from app.models.question import Question
from app.models.student_answer import StudentAnswer
from app.models.evaluation import Evaluation
from app.utils.security import get_password_hash
import datetime

BASE_URL = "http://127.0.0.1:8001"

def login(email, password, role="professor"):
    json_data = {"email": email, "password": password} if role == "professor" else {"identifier": email, "password": password}
    r = requests.post(f"{BASE_URL}/auth/{role}/login", json=json_data)
    if r.status_code == 200:
        return {"Authorization": f"Bearer {r.json().get('access_token')}"}
    return None

def setup_data():
    db = SessionLocal()
    
    # Professors
    prof_a = db.query(Professor).filter(Professor.email == "profa17@vit.ac.in").first()
    if not prof_a:
        prof_a = Professor(name="Prof A17", email="profa17@vit.ac.in", department="CSE", password_hash=get_password_hash("password123"))
        db.add(prof_a)
        
    prof_b = db.query(Professor).filter(Professor.email == "profb17@vit.ac.in").first()
    if not prof_b:
        prof_b = Professor(name="Prof B17", email="profb17@vit.ac.in", department="CSE", password_hash=get_password_hash("password123"))
        db.add(prof_b)
    db.commit()
        
    # Students
    stud_a = db.query(Student).filter(Student.email == "studa17@vit.ac.in").first()
    if not stud_a:
        stud_a = Student(name="Student A17", roll_number="23BCE9917A", email="studa17@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_a)
        
    stud_b = db.query(Student).filter(Student.email == "studb17@vit.ac.in").first()
    if not stud_b:
        stud_b = Student(name="Student B17", roll_number="23BCE9917B", email="studb17@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_b)
        
    stud_c = db.query(Student).filter(Student.email == "studc17@vit.ac.in").first()
    if not stud_c:
        stud_c = Student(name="Student C17", roll_number="23BCE9917C", email="studc17@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_c)
        
    db.commit()
    
    # Subject
    subj = db.query(Subject).filter(Subject.code == "SUB17").first()
    if not subj:
        subj = Subject(name="Subject 17", code="SUB17")
        db.add(subj)
        db.commit()
    
    import time
    unique_ext = str(int(time.time()))
    exam_a_name = f"Phase 17 Test {unique_ext}"
    exam_a = Exam(subject_id=subj.id, professor_id=prof_a.id, name=exam_a_name, total_marks=100, exam_date=datetime.date.today())
    db.add(exam_a)
    db.commit()
        
    # Questions
    q1 = db.query(Question).filter(Question.exam_id == exam_a.id, Question.question_number == "1").first()
    if not q1:
        q1 = Question(exam_id=exam_a.id, question_number="1", question_text="Q1", max_marks=10)
        q2 = Question(exam_id=exam_a.id, question_number="2", question_text="Q2", max_marks=10)
        q3 = Question(exam_id=exam_a.id, question_number="3", question_text="Q3", max_marks=10)
        db.add_all([q1, q2, q3])
        db.commit()
    else:
        q2 = db.query(Question).filter(Question.exam_id == exam_a.id, Question.question_number == "2").first()
        q3 = db.query(Question).filter(Question.exam_id == exam_a.id, Question.question_number == "3").first()
        
    # Scripts
    # Stud A: fully approved (8, 7, 9)
    script_a = db.query(AnswerScript).filter(AnswerScript.exam_id == exam_a.id, AnswerScript.student_id == stud_a.id).first()
    if not script_a:
        script_a = AnswerScript(exam_id=exam_a.id, student_id=stud_a.id, file_path="dummy17_A")
        db.add(script_a)
        db.commit()
        
        sa1 = StudentAnswer(answer_script_id=script_a.id, question_id=q1.id, answer_text="Ans1")
        sa2 = StudentAnswer(answer_script_id=script_a.id, question_id=q2.id, answer_text="Ans2")
        sa3 = StudentAnswer(answer_script_id=script_a.id, question_id=q3.id, answer_text="Ans3")
        db.add_all([sa1, sa2, sa3])
        db.commit()
        
        ev1 = Evaluation(student_answer_id=sa1.id, awarded_marks=6, final_marks=8, review_status="approved")
        ev2 = Evaluation(student_answer_id=sa2.id, awarded_marks=6, final_marks=7, review_status="approved")
        ev3 = Evaluation(student_answer_id=sa3.id, awarded_marks=6, final_marks=9, review_status="approved")
        db.add_all([ev1, ev2, ev3])
        db.commit()
        
    # Stud B: partial approved (appr, appr, under_review)
    script_b = db.query(AnswerScript).filter(AnswerScript.exam_id == exam_a.id, AnswerScript.student_id == stud_b.id).first()
    if not script_b:
        script_b = AnswerScript(exam_id=exam_a.id, student_id=stud_b.id, file_path="dummy17_B")
        db.add(script_b)
        db.commit()
        
        sa1b = StudentAnswer(answer_script_id=script_b.id, question_id=q1.id, answer_text="Ans1")
        sa2b = StudentAnswer(answer_script_id=script_b.id, question_id=q2.id, answer_text="Ans2")
        sa3b = StudentAnswer(answer_script_id=script_b.id, question_id=q3.id, answer_text="Ans3")
        db.add_all([sa1b, sa2b, sa3b])
        db.commit()
        
        ev1b = Evaluation(student_answer_id=sa1b.id, final_marks=5, review_status="approved")
        ev2b = Evaluation(student_answer_id=sa2b.id, final_marks=5, review_status="approved")
        ev3b = Evaluation(student_answer_id=sa3b.id, final_marks=None, review_status="under_review")
        db.add_all([ev1b, ev2b, ev3b])
        db.commit()
        
    # Stud C: NO script (Not submitted)
    # Don't create script for stud C
    
    ids = {
        "exam_a_id": exam_a.id,
        "stud_a_id": stud_a.id,
        "stud_b_id": stud_b.id,
        "stud_c_id": stud_c.id,
        "eval_q1_id": db.query(Evaluation).filter(Evaluation.student_answer_id == db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == script_a.id, StudentAnswer.question_id == q1.id).first().id).first().id
    }
    db.close()
    return ids

def run_tests():
    ids = setup_data()
    exam_id = ids["exam_a_id"]
    stud_a_id = ids["stud_a_id"]
    eval_id = ids["eval_q1_id"]
    
    prof_a = login("profa17@vit.ac.in", "password123", "professor")
    prof_b = login("profb17@vit.ac.in", "password123", "professor")
    stud_a = login("studa17@vit.ac.in", "password123", "student")
    stud_b = login("studb17@vit.ac.in", "password123", "student")
    stud_c = login("studc17@vit.ac.in", "password123", "student")
    
    print("TEST 1 Unauthenticated user requests results.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/results")
    assert r.status_code == 401
    print("PASS")
    
    print("TEST 2 Student requests own results.")
    r = requests.get(f"{BASE_URL}/students/me/results", headers=stud_a)
    assert r.status_code == 200
    res = r.json()
    assert len(res) > 0
    print("PASS")
    
    print("TEST 3 Student attempts to access another student's result.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/students/{ids['stud_b_id']}/result", headers=stud_a)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 4 Student attempts to access professor result endpoint.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/results", headers=stud_a)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 5 Professor requests results for their own exam.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/results", headers=prof_a)
    assert r.status_code == 200
    res = r.json()
    # At least stud a and b should be there
    assert len(res) >= 2
    print("PASS")
    
    print("TEST 6 Professor requests another professor's exam results.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/results", headers=prof_b)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 7 Multiple questions logic & AI vs Final Marks.")
    # Stud A has 8, 7, 9 (AI was 6 for all) -> Total 24, max 30
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/students/{ids['stud_a_id']}/result", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert data["total_marks"] == 24.0
    assert data["maximum_marks"] == 30.0
    assert data["percentage"] == 80.0
    assert data["status"] == "COMPLETED"
    
    q1 = next(q for q in data["questions"] if q["question_number"] == "1")
    assert q1["ai_suggested_marks"] == 6.0
    assert q1["final_marks"] == 8.0
    print("PASS")
    
    print("TEST 8 Unapproved evaluation logic.")
    # Stud B has appr, appr, under_review
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/students/{ids['stud_b_id']}/result", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "PENDING_REVIEW"
    print("PASS")
    
    print("TEST 9 Result regeneration.")
    # Unlock Q1, change final marks to 9, approve
    # First we have to clear approved status directly in DB or via API if we hadn't blocked it (blocked by 409).
    # I'll just use DB
    db = SessionLocal()
    ev = db.query(Evaluation).filter(Evaluation.id == eval_id).first()
    ev.review_status = "under_review"
    db.commit()
    
    r = requests.patch(f"{BASE_URL}/evaluations/{eval_id}/review", json={"final_marks": 9}, headers=prof_a)
    assert r.status_code == 200
    r = requests.post(f"{BASE_URL}/evaluations/{eval_id}/approve", headers=prof_a)
    assert r.status_code == 200
    
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/students/{ids['stud_a_id']}/result", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert data["total_marks"] == 25.0
    assert data["percentage"] == 83.33
    print("PASS")
    
    db.close()
    
    print("TEST 10 Missing submission logic.")
    # Stud C didn't upload script
    # We don't have an endpoint for single student result if script missing? Yes, generate_student_exam_result handles it.
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/students/{ids['stud_c_id']}/result", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "NOT_SUBMITTED"
    assert data["total_marks"] == 0.0
    assert data["percentage"] == 0.0
    print("PASS")

if __name__ == "__main__":
    run_tests()
