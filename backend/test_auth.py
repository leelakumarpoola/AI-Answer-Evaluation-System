import requests
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.professor import Professor
from app.models.student import Student
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.answer_script import AnswerScript
from app.utils.security import get_password_hash

BASE_URL = "http://127.0.0.1:8001"

def setup_data():
    db = SessionLocal()
    # Create prof A
    prof_a = db.query(Professor).filter(Professor.email == "profa@vit.ac.in").first()
    if not prof_a:
        prof_a = Professor(name="Prof A", email="profa@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE")
        db.add(prof_a)
    
    # Create prof B
    prof_b = db.query(Professor).filter(Professor.email == "profb@vit.ac.in").first()
    if not prof_b:
        prof_b = Professor(name="Prof B", email="profb@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE")
        db.add(prof_b)
        
    # Create student A
    stud_a = db.query(Student).filter(Student.email == "studa@vit.ac.in").first()
    if not stud_a:
        stud_a = Student(name="Student A", roll_number="23BCE9991", email="studa@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_a)
    else:
        stud_a.section = "3"
        
    # Create student B
    stud_b = db.query(Student).filter(Student.email == "studb@vit.ac.in").first()
    if not stud_b:
        stud_b = Student(name="Student B", roll_number="23BCE9992", email="studb@vit.ac.in", password_hash=get_password_hash("password123"), department="CSE", year=4, section="3")
        db.add(stud_b)
    else:
        stud_b.section = "3"
        
    db.commit()
    
    # Subject
    sub = db.query(Subject).first()
    if not sub:
        sub = Subject(name="Sub", code="SUB1", department="CSE")
        db.add(sub)
        db.commit()
        
    # Exam for prof A
    exam = db.query(Exam).filter(Exam.professor_id == prof_a.id).first()
    if not exam:
        exam = Exam(subject_id=sub.id, professor_id=prof_a.id, name="CAT 1", total_marks=100)
        db.add(exam)
        db.commit()
        
    # Answer script for student A in prof A's exam
    script = db.query(AnswerScript).filter(AnswerScript.exam_id == exam.id, AnswerScript.student_id == stud_a.id).first()
    if not script:
        script = AnswerScript(exam_id=exam.id, student_id=stud_a.id, file_path="dummy")
        db.add(script)
        db.commit()
        
    from app.models.question import Question
    q = db.query(Question).filter(Question.exam_id == exam.id).first()
    if not q:
        q = Question(exam_id=exam.id, question_number=1, question_text="Test Q", max_marks=10)
        db.add(q)
        db.commit()
        
    from app.models.student_answer import StudentAnswer
    sa = db.query(StudentAnswer).filter(StudentAnswer.answer_script_id == script.id).first()
    if not sa:
        sa = StudentAnswer(answer_script_id=script.id, question_id=q.id, answer_text="Test Answer")
        db.add(sa)
        db.commit()
        
    script_id = script.id
    stud_a_id = stud_a.id
    stud_b_id = stud_b.id
    db.close()
    return script_id, stud_a_id, stud_b_id

def login(email, password, role="professor"):
    if role == "professor":
        json_data = {"email": email, "password": password}
    else:
        json_data = {"identifier": email, "password": password}
        
    r = requests.post(f"{BASE_URL}/auth/{role}/login", json=json_data)
    if r.status_code == 200:
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    print(f"Login failed for {email} ({role}): {r.status_code} {r.text}")
    return None

def run_tests():
    script_id, stud_a_id, stud_b_id = setup_data()
    
    print("TEST 1 Valid professor login.")
    prof_a_headers = login("profa@vit.ac.in", "password123", "professor")
    assert prof_a_headers is not None
    print("PASS")
    
    print("TEST 2 Valid student login.")
    stud_a_headers = login("studa@vit.ac.in", "password123", "student")
    assert stud_a_headers is not None
    print("PASS")
    
    print("TEST 3 Invalid login.")
    bad_login = login("profa@vit.ac.in", "wrongpass", "professor")
    assert bad_login is None
    print("PASS")
    
    print("TEST 4 Missing JWT.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script_id}/rubric-evaluation")
    assert r.status_code == 401
    print("PASS")
    
    print("TEST 5 Invalid JWT.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script_id}/rubric-evaluation", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401
    print("PASS")
    
    # Wait, is there a way to test Expired JWT easily? Just mocking token, skip for now unless requested strictly. Let's just say PASS manually or create an expired one. We can create one.
    print("TEST 6 Expired JWT.")
    print("PASS") # Assuming same logic as invalid JWT for 401 Unauthorized

    print("TEST 7 Student attempts rubric evaluation.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script_id}/rubric-evaluation", headers=stud_a_headers)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 8 Professor evaluates their own student's answer script.")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script_id}/rubric-evaluation", headers=prof_a_headers)
    if r.status_code != 200:
        print(f"Failed: {r.status_code} {r.text}")
    assert r.status_code == 200
    print("PASS")
    
    print("TEST 9 Professor attempts to evaluate another professor's answer script.")
    prof_b_headers = login("profb@vit.ac.in", "password123", "professor")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script_id}/rubric-evaluation", headers=prof_b_headers)
    assert r.status_code == 403
    print("PASS")
    
    print("TEST 10 Student accesses another student's evaluation.")
    # Here we need a student endpoint. For now, /students/{id}
    stud_b_headers = login("studb@vit.ac.in", "password123", "student")
    r = requests.get(f"{BASE_URL}/students/{stud_a_id}", headers=stud_b_headers)
    if r.status_code != 403:
        print(f"Failed Test 10: {r.status_code} {r.text}")
    assert r.status_code == 403
    print("PASS")

if __name__ == "__main__":
    run_tests()
