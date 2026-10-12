import requests
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

BASE_URL = "http://127.0.0.1:8001"

def create_pdf(filename, pages_texts):
    c = canvas.Canvas(filename, pagesize=letter)
    for text_lines in pages_texts:
        y = 750
        for line in text_lines:
            c.drawString(50, y, line)
            y -= 20
        c.showPage()
    c.save()

def run_phase12():
    print("Testing Phase 12...")
    
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
    
    s_id = 1
    pdf_name = f"student_{s_id}_phase12_test.pdf"
    
    pages = [
        ["Student ID: 1", "Q1.", "Blockchain is a distributed ledger.", "It consists of blocks."],
        ["and they are linked cryptographically.", "Q2.", "Consensus mechanisms"],
        ["are very important for trust.", "Q4.", "What about this?"]
    ]
    create_pdf(pdf_name, pages)
    
    # 1. Upload
    with open(pdf_name, "rb") as f:
        r = requests.post(
            f"{BASE_URL}/exams/{exam_id}/students/{s_id}/answer-script", 
            headers=prof_headers, 
            files={"file": (pdf_name, f, "application/pdf")}
        )
    assert r.status_code == 200, f"Upload failed: {r.text}"
    ans_id = r.json()["id"]
    
    # 2. Process
    r = requests.post(f"{BASE_URL}/answer-scripts/{ans_id}/process", headers=prof_headers)
    assert r.status_code == 200, f"Process failed: {r.text}"
    
    # 3. OCR
    r = requests.post(f"{BASE_URL}/answer-scripts/{ans_id}/ocr", headers=prof_headers)
    assert r.status_code == 200, f"OCR failed: {r.text}"
    
    # 4. Extract Answers
    r = requests.post(f"{BASE_URL}/answer-scripts/{ans_id}/extract-answers", headers=prof_headers)
    assert r.status_code == 200, f"Extraction failed: {r.text}"
    
    data = r.json()
    print("Extraction Result:")
    for ans in data["answers"]:
        print(f"Q{ans['question_number']} (Status: {ans['status']}, Pages: {ans['start_page']}-{ans['end_page']}): {ans['answer_text']}")
        
    print("Phase 12 test complete!")

if __name__ == "__main__":
    run_phase12()
