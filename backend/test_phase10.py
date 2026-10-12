import requests
import os
import time
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = "http://127.0.0.1:8001"

def create_pdf(filename, text_lines):
    c = canvas.Canvas(filename, pagesize=letter)
    y = 750
    for line in text_lines:
        c.drawString(50, y, line)
        y -= 20
    c.save()

def run_phase10():
    print("Testing Phase 10...")
    
    # 1. Login
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    assert r.status_code == 200, "Login failed"
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    # 2. Get Exam
    r = requests.get(f"{BASE_URL}/exams/", headers=prof_headers)
    exams = r.json()
    exam = next(e for e in exams if "Blockchain Architecture" in e["name"])
    exam_id = exam["id"]
    
    # 3. Create PDFs
    create_pdf("qp.pdf", [
        "Blockchain Architecture Design - Internal Assessment 1",
        "",
        "Q1. Explain blockchain architecture.",
        "10 Marks",
        "",
        "Q2 Describe consensus mechanisms.",
        "Marks: 15"
    ])
    
    create_pdf("ma.pdf", [
        "Model Answer",
        "",
        "Q1.",
        "Blockchain consists of a decentralized network of nodes.",
        "",
        "Q2",
        "Consensus mechanisms ensure all nodes agree on the state."
    ])
    
    create_pdf("rubric.pdf", [
        "Marks Rubric",
        "",
        "Q1",
        "Architecture explanation - 4 marks",
        "Components - 3 marks",
        "Advantages - 3 marks",
        "",
        "Q2",
        "Proof of Work - 5 marks",
        "Proof of Stake - 5 marks",
        "Others - 5 marks"
    ])
    
    docs = [
        ("question_paper", "qp.pdf"),
        ("model_answer", "ma.pdf"),
        ("marks_rubric", "rubric.pdf")
    ]
    
    for doc_type, filename in docs:
        print(f"Processing {doc_type}...")
        
        # Upload
        with open(filename, "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": doc_type}, files={"file": (filename, f, "application/pdf")})
        assert r.status_code == 201
        doc_id = r.json()["id"]
        
        # Process Images
        r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/process", headers=prof_headers)
        assert r.status_code == 200
        
        # OCR
        r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/ocr", headers=prof_headers)
        assert r.status_code == 200
        
        # Extract
        r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/extract", headers=prof_headers)
        print(f"Extraction result for {doc_type}:")
        print(r.json())
        assert r.status_code == 200
        
        # Verify Retrieval
        r = requests.get(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/extraction", headers=prof_headers)
        assert r.status_code == 200
        
        if doc_type == "question_paper":
            q_data = r.json()
            assert len(q_data["questions"]) >= 2
            assert q_data["questions"][0]["max_marks"] == 10
            
        if doc_type == "model_answer":
            ma_data = r.json()
            assert len(ma_data["model_answers"]) >= 2, "Expected 2 model answers"
            
        if doc_type == "marks_rubric":
            rubric_data = r.json()
            assert len(rubric_data["rubrics"]) >= 2, "Expected 2 question rubrics"
            
    print("Phase 10 test passed successfully.")

if __name__ == "__main__":
    run_phase10()
