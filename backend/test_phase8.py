import requests
import os
import json

BASE_URL = "http://127.0.0.1:8002"

def create_valid_pdf(filename):
    # minimal valid pdf with 1 page
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [ 3 0 R ]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [ 0 0 612 792 ]\n/Resources << >>\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n198\n%%EOF\n"
    with open(filename, "wb") as f:
        f.write(content)

def run_phase8_tests():
    print("Testing Phase 8 endpoints...")
    
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    assert r.status_code == 200, "Failed to login as Professor"
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    student_login = {"identifier": "23BCE0001", "password": "studentpassword123"}
    r = requests.post(f"{BASE_URL}/auth/student/login", json=student_login)
    student_token = r.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    r = requests.get(f"{BASE_URL}/exams/", headers=prof_headers)
    exams = r.json()
    exam = next(e for e in exams if e["name"] == "Blockchain Architecture Design - Internal Assessment 1")
    exam_id = exam["id"]
    
    create_valid_pdf("valid_qp.pdf")
    
    # Upload
    with open("valid_qp.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "question_paper"}, files={"file": ("valid_qp.pdf", f, "application/pdf")})
    assert r.status_code == 201
    doc_id = r.json()["id"]
    
    # Process Unauthenticated
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/process")
    assert r.status_code == 401
    
    # Process Student
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/process", headers=student_headers)
    assert r.status_code == 403
    
    # Process Invalid Document
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/9999/process", headers=prof_headers)
    assert r.status_code == 404
    
    # Process Valid
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/process", headers=prof_headers)
    print(r.json())
    assert r.status_code == 200
    assert r.json()["processing_status"] == "processed"
    assert r.json()["page_count"] == 1
    assert r.json()["processed_page_count"] == 1
    
    # Check Pages
    r = requests.get(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/pages", headers=prof_headers)
    assert r.status_code == 200
    pages = r.json()
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert pages[0]["file_name"] == "page_001.png"
    
    # Verify filesystem
    processed_dir = os.path.join("uploads", "processed", "exams", str(exam_id), str(doc_id))
    assert os.path.exists(processed_dir)
    assert "page_001.png" in os.listdir(processed_dir)
    
    print("Phase 8 tests passed.")

if __name__ == "__main__":
    run_phase8_tests()
