import requests
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = "http://127.0.0.1:8001"

def create_pdf(filename, text_lines):
    c = canvas.Canvas(filename, pagesize=letter)
    y = 750
    for line in text_lines:
        c.drawString(50, y, line)
        y -= 20
    # Add a second page just to test multi-page
    c.showPage()
    c.drawString(50, 750, "Page 2: continued...")
    c.save()

def run_phase11():
    print("Testing Phase 11...")
    
    # Login
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    assert r.status_code == 200, "Login failed"
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    # Get Exam
    r = requests.get(f"{BASE_URL}/exams/", headers=prof_headers)
    exams = r.json()
    exam = next(e for e in exams if "Blockchain Architecture" in e["name"])
    exam_id = exam["id"]
    
    # Get Students (Assume 23BCE0001 is student_id=1, 23BCE0002 is student_id=2)
    students_list = [1, 2, 3]
    
    for s_id in students_list:
        pdf_name = f"student_{s_id}_answer.pdf"
        create_pdf(pdf_name, [f"Student ID: {s_id}", "Q1.", "Blockchain is a distributed ledger."])
        
        # 1. Upload
        with open(pdf_name, "rb") as f:
            r = requests.post(
                f"{BASE_URL}/exams/{exam_id}/students/{s_id}/answer-script", 
                headers=prof_headers, 
                files={"file": (pdf_name, f, "application/pdf")}
            )
        assert r.status_code == 200, f"Upload failed for {s_id}: {r.text}"
        ans_id = r.json()["id"]
        
        # 2. Process
        r = requests.post(f"{BASE_URL}/answer-scripts/{ans_id}/process", headers=prof_headers)
        assert r.status_code == 200, f"Process failed: {r.text}"
        
        # 3. OCR
        r = requests.post(f"{BASE_URL}/answer-scripts/{ans_id}/ocr", headers=prof_headers)
        assert r.status_code == 200, f"OCR failed: {r.text}"
        
        # 4. Fetch Results
        r = requests.get(f"{BASE_URL}/answer-scripts/{ans_id}/ocr", headers=prof_headers)
        assert r.status_code == 200
        data = r.json()
        assert len(data["pages"]) == 2
        print(f"Student {s_id} script processed and OCR'd successfully.")

    print("Phase 11 test passed!")

if __name__ == "__main__":
    run_phase11()
