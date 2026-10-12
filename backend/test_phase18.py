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
import time

BASE_URL = "http://127.0.0.1:8001"

def login(email, password, role="professor"):
    json_data = {"email": email, "password": password} if role == "professor" else {"identifier": email, "password": password}
    r = requests.post(f"{BASE_URL}/auth/{role}/login", json=json_data)
    if r.status_code == 200:
        return {"Authorization": f"Bearer {r.json().get('access_token')}"}
    return None

def setup_data():
    db = SessionLocal()
    unique_ext = str(int(time.time()))
    
    prof_a = db.query(Professor).filter(Professor.email == "profa18@vit.ac.in").first()
    if not prof_a:
        prof_a = Professor(name="Prof A18", email="profa18@vit.ac.in", department="CSE", password_hash=get_password_hash("password123"))
        db.add(prof_a)
        
    prof_b = db.query(Professor).filter(Professor.email == "profb18@vit.ac.in").first()
    if not prof_b:
        prof_b = Professor(name="Prof B18", email="profb18@vit.ac.in", department="CSE", password_hash=get_password_hash("password123"))
        db.add(prof_b)
    db.commit()
        
    # Students
    stud_1 = db.query(Student).filter(Student.email == "stud1_18@vit.ac.in").first()
    if not stud_1:
        stud_1 = Student(name="Student 1 18", roll_number="23BCE9918A", email="stud1_18@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_1)
        
    stud_2 = db.query(Student).filter(Student.email == "stud2_18@vit.ac.in").first()
    if not stud_2:
        stud_2 = Student(name="Student 2 18", roll_number="23BCE9918B", email="stud2_18@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_2)
        
    stud_3 = db.query(Student).filter(Student.email == "stud3_18@vit.ac.in").first()
    if not stud_3:
        stud_3 = Student(name="Student 3 18", roll_number="23BCE9918C", email="stud3_18@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_3)
        
    db.commit()
    
    subj = db.query(Subject).filter(Subject.code == "SUB18").first()
    if not subj:
        subj = Subject(name="Subject 18", code="SUB18")
        db.add(subj)
        db.commit()
    
    exam_name = f"Phase 18 Test {unique_ext}"
    exam = Exam(subject_id=subj.id, professor_id=prof_a.id, name=exam_name, total_marks=100, exam_date=datetime.date.today())
    db.add(exam)
    db.commit()
        
    # Questions
    q1 = Question(exam_id=exam.id, question_number="1", question_text="Q1", max_marks=10)
    q2 = Question(exam_id=exam.id, question_number="2", question_text="Q2", max_marks=10)
    q3 = Question(exam_id=exam.id, question_number="3", question_text="Q3", max_marks=10)
    db.add_all([q1, q2, q3])
    db.commit()
        
    # Stud 1: Total 24 (8, 7, 9)
    script_1 = AnswerScript(exam_id=exam.id, student_id=stud_1.id, file_path="dummy18_1")
    db.add(script_1)
    db.commit()
    sa1_1 = StudentAnswer(answer_script_id=script_1.id, question_id=q1.id, answer_text="Ans1")
    sa1_2 = StudentAnswer(answer_script_id=script_1.id, question_id=q2.id, answer_text="Ans2")
    sa1_3 = StudentAnswer(answer_script_id=script_1.id, question_id=q3.id, answer_text="Ans3")
    db.add_all([sa1_1, sa1_2, sa1_3])
    db.commit()
    ev1_1 = Evaluation(student_answer_id=sa1_1.id, awarded_marks=6, final_marks=8, review_status="approved")
    ev1_2 = Evaluation(student_answer_id=sa1_2.id, awarded_marks=5, final_marks=7, review_status="approved")
    ev1_3 = Evaluation(student_answer_id=sa1_3.id, awarded_marks=6, final_marks=9, review_status="approved")
    db.add_all([ev1_1, ev1_2, ev1_3])
    db.commit()
    
    # Stud 2: Total 21 (6, 8, 7)
    script_2 = AnswerScript(exam_id=exam.id, student_id=stud_2.id, file_path="dummy18_2")
    db.add(script_2)
    db.commit()
    sa2_1 = StudentAnswer(answer_script_id=script_2.id, question_id=q1.id, answer_text="Ans1")
    sa2_2 = StudentAnswer(answer_script_id=script_2.id, question_id=q2.id, answer_text="Ans2")
    sa2_3 = StudentAnswer(answer_script_id=script_2.id, question_id=q3.id, answer_text="Ans3")
    db.add_all([sa2_1, sa2_2, sa2_3])
    db.commit()
    ev2_1 = Evaluation(student_answer_id=sa2_1.id, awarded_marks=2, final_marks=6, review_status="approved")
    ev2_2 = Evaluation(student_answer_id=sa2_2.id, awarded_marks=2, final_marks=8, review_status="approved")
    ev2_3 = Evaluation(student_answer_id=sa2_3.id, awarded_marks=2, final_marks=7, review_status="approved")
    db.add_all([ev2_1, ev2_2, ev2_3])
    db.commit()
    
    # Stud 3: Total 27 (10, 9, 8)
    script_3 = AnswerScript(exam_id=exam.id, student_id=stud_3.id, file_path="dummy18_3")
    db.add(script_3)
    db.commit()
    sa3_1 = StudentAnswer(answer_script_id=script_3.id, question_id=q1.id, answer_text="Ans1")
    sa3_2 = StudentAnswer(answer_script_id=script_3.id, question_id=q2.id, answer_text="Ans2")
    sa3_3 = StudentAnswer(answer_script_id=script_3.id, question_id=q3.id, answer_text="Ans3")
    db.add_all([sa3_1, sa3_2, sa3_3])
    db.commit()
    # Let's make q1 for stud 3 UNAPPROVED originally to test the reopen/reapprove
    ev3_1 = Evaluation(student_answer_id=sa3_1.id, awarded_marks=9, final_marks=10, review_status="under_review")
    ev3_2 = Evaluation(student_answer_id=sa3_2.id, awarded_marks=9, final_marks=9, review_status="approved")
    ev3_3 = Evaluation(student_answer_id=sa3_3.id, awarded_marks=9, final_marks=8, review_status="approved")
    db.add_all([ev3_1, ev3_2, ev3_3])
    db.commit()

    ids = {
        "exam_id": exam.id,
        "eval_unapproved_id": ev3_1.id
    }
    db.close()
    return ids

def run_tests():
    ids = setup_data()
    exam_id = ids["exam_id"]
    eval_unapproved_id = ids["eval_unapproved_id"]
    
    prof_a = login("profa18@vit.ac.in", "password123", "professor")
    prof_b = login("profb18@vit.ac.in", "password123", "professor")
    stud_1 = login("stud1_18@vit.ac.in", "password123", "student")
    
    print("TEST 1 Exam summary report.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert data["students_completed"] == 2
    assert data["students_pending"] == 1
    # Average of 24 and 21 is 22.5
    assert data["average_marks"] == 22.5
    assert data["highest_marks"] == 24.0
    assert data["lowest_marks"] == 21.0
    assert data["median_marks"] == 22.5
    print("PASS")

    print("TEST 2 Student performance report.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/students", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 3
    print("PASS")

    print("TEST 3 Question performance report.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/questions", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    q1 = next(q for q in data if q["question_number"] == "1")
    # Q1 has two approved: 8 and 6 -> avg 7.0
    assert q1["average_marks"] == 7.0
    assert q1["highest_marks"] == 8.0
    assert q1["students_evaluated"] == 2
    assert q1["performance_category"] == "MEDIUM_PERFORMANCE" # 70%
    print("PASS")

    print("TEST 4 Marks distribution.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/distribution", headers=prof_a)
    assert r.status_code == 200
    dist = r.json()["distribution"]
    # 24/30 = 80%, 21/30 = 70%.
    assert dist["80-89"] == 1
    assert dist["70-79"] == 1
    assert dist["90-100"] == 0
    print("PASS")

    print("TEST 5 Completion report.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/completion", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    assert data["students_with_approved_results"] == 2
    assert data["students_pending_review"] == 1
    print("PASS")

    print("TEST 6 Approved-only filtering.")
    # Validated by median/averages logic in TEST 1 & TEST 3
    print("PASS")

    print("TEST 7 AI-vs-final marks test.")
    # Validated in TEST 3 since AI marks were 6, 2 and Final were 8, 6. Average of final is 7. (If AI used it'd be 4)
    print("PASS")

    print("TEST 8 Unapproved evaluation test.")
    # Validated in TEST 1 and TEST 3 where the 3rd student wasn't included in stats yet
    print("PASS")

    print("TEST 9 Reopen/reapprove test.")
    # Reapprove 3rd student's Q1
    # First, let's approve it.
    r = requests.post(f"{BASE_URL}/evaluations/{eval_unapproved_id}/approve", headers=prof_a)
    assert r.status_code == 200
    
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers=prof_a)
    assert r.status_code == 200
    data = r.json()
    # Now students_completed should be 3
    assert data["students_completed"] == 3
    # Averages of 24, 21, 27 -> sum 72 / 3 = 24.0
    assert data["average_marks"] == 24.0
    assert data["highest_marks"] == 27.0
    assert data["lowest_marks"] == 21.0
    assert data["median_marks"] == 24.0
    
    # Now reopen Q1 for student 3 by changing DB directly since Phase 16 locks approved records
    db = SessionLocal()
    ev = db.query(Evaluation).filter(Evaluation.id == eval_unapproved_id).first()
    ev.review_status = "under_review"
    db.commit()
    
    r = requests.patch(f"{BASE_URL}/evaluations/{eval_unapproved_id}/review", json={"final_marks": 5}, headers=prof_a)
    assert r.status_code == 200
    
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers=prof_a)
    data = r.json()
    # Back to pending! So stats should match TEST 1 exactly again
    assert data["students_completed"] == 2
    assert data["students_pending"] == 1
    assert data["average_marks"] == 22.5
    print("PASS")

    print("TEST 10 Professor authorization.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers=prof_a)
    assert r.status_code == 200
    print("PASS")

    print("TEST 11 Student restriction.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers=stud_1)
    assert r.status_code == 403
    print("PASS")

    print("TEST 12 Wrong professor restriction.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers=prof_b)
    assert r.status_code == 403
    print("PASS")

    print("TEST 13 Invalid token handling.")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/reports/summary", headers={"Authorization": "Bearer BADTOKEN"})
    assert r.status_code == 401
    print("PASS")

if __name__ == "__main__":
    run_tests()
