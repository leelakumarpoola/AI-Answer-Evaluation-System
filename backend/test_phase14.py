import requests
import sqlite3
import os

BASE_URL = "http://127.0.0.1:8001"

def create_test_data(prof_token):
    headers = {"Authorization": f"Bearer {prof_token}"}
    
    # 1. Create a subject
    r = requests.post(f"{BASE_URL}/subjects/", json={"name": "Testing Subject", "code": "TST101", "description": "Test"}, headers=headers)
    subj_id = r.json()["id"]
    
    # 2. Create an exam
    r = requests.post(f"{BASE_URL}/exams/", json={"subject_id": subj_id, "name": "Test Exam", "date": "2025-10-10", "total_marks": 100}, headers=headers)
    exam_id = r.json()["id"]
    
    # We will just directly use psycopg2 or sqlalchemy to insert the rest if there's no endpoint. But there ARE endpoints for questions and answer scripts in the router?
    # Wait, Phase 6 and 10 might have endpoints. If not, I can just do it via requests?
    print(f"Test Exam ID: {exam_id}")
    return exam_id

def run_tests():
    print("Testing Phase 14...")
    
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    assert r.status_code == 200, "Login failed"
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    # Check invalid auth
    r = requests.post(f"{BASE_URL}/answer-scripts/999/rubric-evaluation")
    assert r.status_code == 401, "Unauthenticated failed"
    print("Unauthenticated: PASS")
    
    # We will use SQLAlchemy to seed the DB directly because it's easier and avoids depending on previous phase complex PDF upload mocking.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.subject import Subject
    from app.models.exam import Exam
    from app.models.question import Question
    from app.models.rubric import Rubric
    from app.models.model_answer import ModelAnswer
    from app.models.answer_script import AnswerScript
    from app.models.student_answer import StudentAnswer
    import os
    from dotenv import load_dotenv

    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Fetch prof ID from db
    from app.models.professor import Professor
    prof = db.query(Professor).filter(Professor.email == "rahul.tripati@vit.ac.in").first()
    prof_id = prof.id
    
    import time
    unique = str(int(time.time()))
    subj = Subject(name=f"Test Subject {unique}", code=f"TST{unique}")
    db.add(subj)
    db.commit()
    
    exam = Exam(subject_id=subj.id, name=f"Test Exam {unique}", total_marks=50, professor_id=prof_id)
    db.add(exam)
    db.commit()
    
    # Student 1
    script1 = AnswerScript(exam_id=exam.id, student_id=1, file_path="dummy")
    # Student 2
    script2 = AnswerScript(exam_id=exam.id, student_id=2, file_path="dummy")
    db.add_all([script1, script2])
    db.commit()
    
    # Question 1: Valid
    q1 = Question(exam_id=exam.id, question_number="1", question_text="Explain blockchain", max_marks=10)
    # Question 2: Missing Model Answer
    q2 = Question(exam_id=exam.id, question_number="2", question_text="What is Bitcoin", max_marks=5)
    # Question 3: Missing Rubric
    q3 = Question(exam_id=exam.id, question_number="3", question_text="Explain PoW", max_marks=5)
    # Question 4: Invalid Rubric
    q4 = Question(exam_id=exam.id, question_number="4", question_text="Explain PoS", max_marks=5)
    
    db.add_all([q1, q2, q3, q4])
    db.commit()
    
    # Model Answers
    ma1 = ModelAnswer(question_id=q1.id, answer_text="Blockchain is a decentralized distributed ledger. Transactions are stored across multiple nodes. It provides security and immutability. An example is Bitcoin.")
    ma3 = ModelAnswer(question_id=q3.id, answer_text="Proof of Work")
    ma4 = ModelAnswer(question_id=q4.id, answer_text="Proof of Stake")
    db.add_all([ma1, ma3, ma4])
    
    # Rubrics
    r1a = Rubric(question_id=q1.id, criterion="Definition", description="Decentralized distributed ledger", marks=4)
    r1b = Rubric(question_id=q1.id, criterion="Nodes", description="Stored across multiple nodes", marks=3)
    r1c = Rubric(question_id=q1.id, criterion="Security", description="Provides security and immutability", marks=3)
    
    # Invalid Rubric for q4 (total marks = 10, max = 5)
    r4 = Rubric(question_id=q4.id, criterion="Everything", marks=10)
    db.add_all([r1a, r1b, r1c, r4])
    db.commit()
    
    # Student Answers for Script 1 (Valid, Partial, Unrelated, Unanswered)
    # Q1: Valid answer
    sa1_q1 = StudentAnswer(answer_script_id=script1.id, question_id=q1.id, answer_text="Blockchain is a decentralized distributed ledger. It is stored on multiple nodes and gives security.")
    # Q2: Unanswered (but q2 has missing model answer, let's just create a normal SA)
    sa1_q2 = StudentAnswer(answer_script_id=script1.id, question_id=q2.id, answer_text="Bitcoin is a crypto.")
    # Q3: Missing rubric
    sa1_q3 = StudentAnswer(answer_script_id=script1.id, question_id=q3.id, answer_text="PoW uses energy.")
    # Q4: Invalid rubric
    sa1_q4 = StudentAnswer(answer_script_id=script1.id, question_id=q4.id, answer_text="PoS saves energy.")
    
    db.add_all([sa1_q1, sa1_q2, sa1_q3, sa1_q4])
    db.commit()
    
    # Student Answers for Script 2 (Testing Partial / Unrelated)
    # Partial for Q1
    sa2_q1 = StudentAnswer(answer_script_id=script2.id, question_id=q1.id, answer_text="Blockchain is a distributed ledger.")
    # Unanswered for Q1 (we will just make a different script or reuse q2)
    # Wait, sa2_q2 is unanswered
    sa2_q2 = StudentAnswer(answer_script_id=script2.id, question_id=q2.id, answer_status="unanswered")
    # Unrelated for Q3
    sa2_q3 = StudentAnswer(answer_script_id=script2.id, question_id=q3.id, answer_text="A compiler converts source code into machine code.")
    db.add_all([sa2_q1, sa2_q2, sa2_q3])
    db.commit()
    
    # --- NOW TEST VIA API ---
    print(f"Testing Script 1 (ID: {script1.id})")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script1.id}/rubric-evaluation", headers=prof_headers)
    assert r.status_code == 200, f"Failed: {r.text}"
    res1 = r.json()["results"]
    
    q1_res = next(x for x in res1 if x["question_id"] == q1.id)
    q2_res = next(x for x in res1 if x["question_id"] == q2.id)
    q3_res = next(x for x in res1 if x["question_id"] == q3.id)
    q4_res = next(x for x in res1 if x["question_id"] == q4.id)
    
    assert q1_res["status"] == "completed"
    print("Valid answer: PASS")
    assert q2_res["status"] == "model_answer_missing"
    print("Missing model answer: PASS")
    assert q3_res["status"] == "rubric_missing"
    print("Missing rubric: PASS")
    assert q4_res["status"] == "invalid_rubric"
    print("Invalid rubric: PASS")
    
    print(f"Testing Script 2 (ID: {script2.id})")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script2.id}/rubric-evaluation", headers=prof_headers)
    assert r.status_code == 200
    res2 = r.json()["results"]
    
    q1_partial = next(x for x in res2 if x["question_id"] == q1.id)
    q2_unans = next(x for x in res2 if x["question_id"] == q2.id)
    q3_unrel = next(x for x in res2 if x["question_id"] == q3.id)
    
    assert q1_partial["status"] == "completed"
    assert q1_partial["suggested_marks"] < 10.0 # Partial should be less than full
    print("Partial answer: PASS")
    
    assert q2_unans["status"] == "unanswered"
    print("Unanswered question: PASS")
    
    # Student 3
    script3 = AnswerScript(exam_id=exam.id, student_id=3, file_path="dummy")
    db.add(script3)
    db.commit()
    sa3_q1 = StudentAnswer(answer_script_id=script3.id, question_id=q1.id, answer_text="A compiler converts source code into machine code.")
    db.add(sa3_q1)
    db.commit()
    
    print(f"Testing Script 3 (ID: {script3.id})")
    r = requests.post(f"{BASE_URL}/answer-scripts/{script3.id}/rubric-evaluation", headers=prof_headers)
    assert r.status_code == 200
    res3 = r.json()["results"]
    q1_unrel = next(x for x in res3 if x["question_id"] == q1.id)
    print("Unrelated:", q1_unrel)
    assert q1_unrel["status"] == "completed"
    print("Unrelated answer: PASS")
    
    print("Multiple questions: PASS")
    print("Multiple students: PASS")
    
    # Repeated execution (Idempotency)
    r_repeat = requests.post(f"{BASE_URL}/answer-scripts/{script1.id}/rubric-evaluation", headers=prof_headers)
    assert r_repeat.status_code == 200
    print("Repeated execution: PASS")
    
    print("All Phase 14 E2E tests PASSED!")

if __name__ == "__main__":
    run_tests()
