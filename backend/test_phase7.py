import requests
import os
import json

BASE_URL = "http://127.0.0.1:8001"

def create_dummy_pdf(filename):
    # Just creating a dummy file with .pdf extension
    with open(filename, "wb") as f:
        f.write(b"%PDF-1.4\n%Dummy PDF content\n")

def run_phase7_tests():
    print("Testing Phase 7 endpoints...")
    
    # 1. Login as Professor
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    assert r.status_code == 200, "Failed to login as Professor"
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    # 2. Login as Student
    student_login = {"identifier": "23BCE0001", "password": "studentpassword123"}
    r = requests.post(f"{BASE_URL}/auth/student/login", json=student_login)
    assert r.status_code == 200, "Failed to login as Student"
    student_token = r.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 3. Get the exam
    r = requests.get(f"{BASE_URL}/exams/", headers=prof_headers)
    exams = r.json()
    exam = next(e for e in exams if e["name"] == "Blockchain Architecture Design - Internal Assessment 1")
    exam_id = exam["id"]
    print(f"Using Exam ID: {exam_id}")

    # 4. Create dummy PDFs and non-PDFs
    create_dummy_pdf("question_paper.pdf")
    create_dummy_pdf("model_answer.pdf")
    create_dummy_pdf("marks_rubric.pdf")
    with open("empty.pdf", "wb") as f: pass
    with open("text.txt", "w") as f: f.write("Hello")
    
    try:
        # Negative Tests
        print("\nRunning Negative Tests...")
        # Unauthenticated
        with open("question_paper.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", data={"document_type": "question_paper"}, files={"file": ("question_paper.pdf", f, "application/pdf")})
        assert r.status_code == 401, "Unauthenticated user could upload"
        
        # Student
        with open("question_paper.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=student_headers, data={"document_type": "question_paper"}, files={"file": ("question_paper.pdf", f, "application/pdf")})
        assert r.status_code == 403, "Student could upload"
        
        # Non-PDF file
        with open("text.txt", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "question_paper"}, files={"file": ("text.txt", f, "text/plain")})
        assert r.status_code == 400, "Allowed non-PDF upload"

        # Empty file
        with open("empty.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "question_paper"}, files={"file": ("empty.pdf", f, "application/pdf")})
        assert r.status_code == 400, "Allowed empty PDF upload"
        
        # Invalid document type
        with open("question_paper.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "invalid_type"}, files={"file": ("q.pdf", f, "application/pdf")})
        assert r.status_code == 400, "Allowed invalid document type"

        print("Negative tests passed.")
        
        print("\nRunning Positive Tests...")
        # Upload question paper
        with open("question_paper.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "question_paper"}, files={"file": ("question_paper.pdf", f, "application/pdf")})
        assert r.status_code == 201, f"Failed to upload question paper: {r.text}"
        qp_doc_id = r.json()["id"]

        # Upload model answer
        with open("model_answer.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "model_answer"}, files={"file": ("model_answer.pdf", f, "application/pdf")})
        assert r.status_code == 201

        # Upload rubric
        with open("marks_rubric.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "marks_rubric"}, files={"file": ("marks_rubric.pdf", f, "application/pdf")})
        assert r.status_code == 201
        
        # Test Duplicate (should update)
        with open("question_paper.pdf", "rb") as f:
            r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "question_paper"}, files={"file": ("question_paper.pdf", f, "application/pdf")})
        assert r.status_code == 201, "Duplicate upload failed"
        assert r.json()["id"] == qp_doc_id, "Duplicate upload created new record instead of updating"
        
        # Get documents
        r = requests.get(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers)
        assert r.status_code == 200
        docs = r.json()
        assert len(docs) == 3, f"Expected 3 documents, got {len(docs)}"
        
        # Download document
        r = requests.get(f"{BASE_URL}/exams/{exam_id}/documents/{qp_doc_id}/download", headers=prof_headers)
        assert r.status_code == 200
        assert b"%PDF-1.4" in r.content
        
        print("Positive tests passed. Phase 7 is fully functional.")

    finally:
        # Cleanup
        for file in ["question_paper.pdf", "model_answer.pdf", "marks_rubric.pdf", "empty.pdf", "text.txt"]:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    run_phase7_tests()
