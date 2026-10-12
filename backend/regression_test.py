import requests
import os

BASE_URL = "http://127.0.0.1:8001"

def create_valid_pdf(filename):
    content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [ 3 0 R ]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [ 0 0 612 792 ]\n/Resources << >>\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n198\n%%EOF\n"
    with open(filename, "wb") as f:
        f.write(content)

def run_regression_tests():
    print("Running Complete Regression Test...")
    
    # Phase 1
    assert requests.get(f"{BASE_URL}/").status_code == 200
    assert requests.get(f"{BASE_URL}/health").status_code == 200
    
    # Phase 2
    db_test = requests.get(f"{BASE_URL}/db-test")
    assert db_test.status_code == 200
    
    # Phase 4 (Students)
    # They should exist via db check but we can't easily query everything via api yet,
    # except login
    
    # Phase 5 (Authentication)
    # Login Prof
    prof_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=prof_data)
    assert r.status_code == 200
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    
    # Login Student
    student_data = {"identifier": "23BCE0001", "password": "studentpassword123"}
    r = requests.post(f"{BASE_URL}/auth/student/login", json=student_data)
    assert r.status_code == 200
    student_token = r.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    # /auth/me
    assert requests.get(f"{BASE_URL}/auth/me", headers=prof_headers).status_code == 200
    
    # Protected endpoints
    assert requests.get(f"{BASE_URL}/auth/professor-test", headers=prof_headers).status_code == 200
    assert requests.get(f"{BASE_URL}/auth/professor-test", headers=student_headers).status_code == 403
    
    # Phase 6
    exams = requests.get(f"{BASE_URL}/exams/", headers=prof_headers).json()
    exam = next(e for e in exams if "Blockchain Architecture" in e["name"])
    exam_id = exam["id"]
    
    # Phase 7
    create_valid_pdf("regression.pdf")
    with open("regression.pdf", "rb") as f:
        r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/", headers=prof_headers, data={"document_type": "model_answer"}, files={"file": ("regression.pdf", f, "application/pdf")})
    assert r.status_code == 201
    doc_id = r.json()["id"]
    
    # Phase 8
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/process", headers=prof_headers)
    assert r.status_code == 200
    assert r.json()["processing_status"] == "processed"
    
    # Phase 9
    r = requests.post(f"{BASE_URL}/exams/{exam_id}/documents/{doc_id}/ocr", headers=prof_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "processed"
    
    print("Regression tests passed successfully!")

if __name__ == "__main__":
    run_regression_tests()
