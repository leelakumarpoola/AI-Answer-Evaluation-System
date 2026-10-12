import requests
import os
import time

BASE_URL = "http://127.0.0.1:8001"

def create_valid_pdf(filename):
    # tiny valid pdf with 1 page
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [ 3 0 R ]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [ 0 0 612 792 ]\n/Resources << >>\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n198\n%%EOF\n"
    with open(filename, "wb") as f:
        f.write(content)

def run_tests():
    print("Testing Phase 9...")
    
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    r = requests.get(f"{BASE_URL}/exams/", headers=prof_headers)
    exam_id = next(e for e in r.json() if e["name"] == "Blockchain Architecture Design - Internal Assessment 1")["id"]
    
    create_valid_pdf("ocr_test.pdf")
    
    with open("ocr_test.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "question_paper"}, files={"file": ("ocr_test.pdf", f, "application/pdf")})
    
    doc_id = r.json()["id"]
    
    # Process PDF -> Images
    requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/process", headers=prof_headers)
    
    # Process OCR
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/ocr", headers=prof_headers)
    print(r.json())
    assert r.status_code == 200
    assert r.json()["status"] == "processed"
    
    # Retrieve OCR
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/ocr", headers=prof_headers)
    assert r.status_code == 200
    assert r.json()["pages"][0]["page_number"] == 1
    
    print("Phase 9 test passed.")

if __name__ == "__main__":
    run_tests()
