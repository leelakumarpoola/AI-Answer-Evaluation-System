import requests
import json
import datetime

BASE_URL = "http://127.0.0.1:8001"

def run_phase6_tests():
    print("Testing Phase 1 (Base endpoints)...")
    assert requests.get(f"{BASE_URL}/").status_code == 200
    assert requests.get(f"{BASE_URL}/health").status_code == 200
    assert requests.get(f"{BASE_URL}/docs").status_code == 200
    assert requests.get(f"{BASE_URL}/redoc").status_code == 200
    print("Phase 1 verified.")

    print("\nTesting Phase 2 (DB Test)...")
    assert requests.get(f"{BASE_URL}/db-test").status_code == 200
    print("Phase 2 verified.")

    print("\nTesting Phase 4 (Student API & Preservation)...")
    r = requests.get(f"{BASE_URL}/students/")
    students = sorted(r.json(), key=lambda x: x["roll_number"])
    assert len(students) >= 30, "Less than 30 students found!"
    assert students[0]["roll_number"] == "23BCE0001"
    assert students[0]["department"] == "Computer Science and Engineering"
    assert students[0]["year"] == 4
    assert students[0]["section"] == "3"
    print("Phase 4 verified. Students preserved.")

    print("\nProvisioning Rahul Tripati...")
    prof_data = {
        "name": "Rahul Tripati",
        "email": "rahul.tripati@vit.ac.in",
        "department": "Computer Science and Engineering",
        "password": "securepassword123"
    }
    r = requests.post(f"{BASE_URL}/auth/professor/register", json=prof_data)
    if r.status_code == 400 and "already registered" in r.text:
        print("Rahul Tripati already exists.")
    else:
        assert r.status_code == 201, "Failed to create Rahul Tripati"

    print("\nLogging in as Rahul Tripati...")
    login_data = {"email": "rahul.tripati@vit.ac.in", "password": "securepassword123"}
    r = requests.post(f"{BASE_URL}/auth/professor/login", json=login_data)
    assert r.status_code == 200
    prof_token = r.json()["access_token"]
    prof_headers = {"Authorization": f"Bearer {prof_token}"}
    print("Professor JWT acquired.")

    print("\nLogging in as a Student for auth testing...")
    r = requests.post(f"{BASE_URL}/auth/student/login", json={"identifier": "23BCE0001", "password": "studentpassword123"})
    if r.status_code == 200:
        student_token = r.json()["access_token"]
    else:
        print("Student not registered in auth, registering...")
        r = requests.post(f"{BASE_URL}/auth/student/register", json={"roll_number": "23BCE0001", "email": "leelakumarp2023@vitstudent.vit.ac.in", "password": "studentpassword123"})
        r = requests.post(f"{BASE_URL}/auth/student/login", json={"identifier": "23BCE0001", "password": "studentpassword123"})
        assert r.status_code == 200
        student_token = r.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    print("\nVerifying /auth/me for Professor...")
    r = requests.get(f"{BASE_URL}/auth/me", headers=prof_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Rahul Tripati"
    
    print("\nTesting Subject validation (Course Code)...")
    bad_subject = {"name": "Bad Subject", "code": "BCSE29L", "department": "CSE"}
    r = requests.post(f"{BASE_URL}/subjects/", json=bad_subject, headers=prof_headers)
    assert r.status_code == 422, f"Failed to reject invalid course code: {r.status_code}"

    bad_subject2 = {"name": "Bad Subject", "code": "BCSE1234L", "department": "CSE"}
    r = requests.post(f"{BASE_URL}/subjects/", json=bad_subject2, headers=prof_headers)
    assert r.status_code == 422

    print("\nProvisioning Blockchain Architecture Design...")
    subject_data = {
        "name": "Blockchain Architecture Design",
        "code": "BCSE329L",
        "department": "Computer Science and Engineering"
    }
    r = requests.post(f"{BASE_URL}/subjects/", json=subject_data, headers=prof_headers)
    if r.status_code == 409:
        print("Subject already exists. Retrieving it.")
        subjects = requests.get(f"{BASE_URL}/subjects/").json()
        subject_id = next(s["id"] for s in subjects if s["code"] == "BCSE329L")
    else:
        assert r.status_code == 201, f"Failed to create subject: {r.text}"
        subject_id = r.json()["id"]

    print("\nTesting duplicate subject creation...")
    r = requests.post(f"{BASE_URL}/subjects/", json=subject_data, headers=prof_headers)
    assert r.status_code == 409, "Did not reject duplicate subject"

    print("\nTesting student access to POST /subjects...")
    r = requests.post(f"{BASE_URL}/subjects/", json={"name": "x", "code": "BCSE999L", "department": "CSE"}, headers=student_headers)
    assert r.status_code == 403, "Student was able to access POST /subjects"

    print("\nTesting student access to POST /exams...")
    r = requests.post(f"{BASE_URL}/exams/", json={"name":"test", "exam_type":"Internal", "subject_id":1, "total_marks":10}, headers=student_headers)
    assert r.status_code == 403, "Student was able to access POST /exams"

    print("\nTesting unauthenticated access to POST /exams...")
    r = requests.post(f"{BASE_URL}/exams/", json={"name":"test", "exam_type":"Internal", "subject_id":1, "total_marks":10})
    assert r.status_code == 401, "Unauthenticated user was able to access POST /exams"

    print("\nTesting GET /subjects...")
    r = requests.get(f"{BASE_URL}/subjects/")
    assert any(s["code"] == "BCSE329L" for s in r.json())
    
    print("\nTesting GET /subjects/{id}...")
    r = requests.get(f"{BASE_URL}/subjects/{subject_id}")
    assert r.json()["code"] == "BCSE329L"

    print("\nTesting Exam Validation...")
    bad_exam = {
        "name": "Test",
        "exam_type": "Internal",
        "subject_id": subject_id,
        "total_marks": 0,
        "duration_minutes": 120
    }
    r = requests.post(f"{BASE_URL}/exams/", json=bad_exam, headers=prof_headers)
    assert r.status_code == 422, "Did not reject 0 total marks"

    bad_exam["total_marks"] = 100
    bad_exam["duration_minutes"] = -10
    r = requests.post(f"{BASE_URL}/exams/", json=bad_exam, headers=prof_headers)
    assert r.status_code == 422, "Did not reject negative duration"

    bad_exam["duration_minutes"] = 120
    bad_exam["subject_id"] = 999999
    r = requests.post(f"{BASE_URL}/exams/", json=bad_exam, headers=prof_headers)
    assert r.status_code == 404, "Did not reject nonexistent subject"

    print("\nProvisioning Exam: Internal Assessment 1...")
    exam_data = {
        "name": "Blockchain Architecture Design - Internal Assessment 1",
        "exam_type": "Internal",
        "subject_id": subject_id,
        "exam_date": "2026-09-25",
        "total_marks": 100,
        "duration_minutes": 120
    }
    r = requests.post(f"{BASE_URL}/exams/", json=exam_data, headers=prof_headers)
    assert r.status_code == 201, f"Failed to create exam: {r.text}"
    exam_id = r.json()["id"]

    print("\nTesting GET /exams...")
    r = requests.get(f"{BASE_URL}/exams/", headers=prof_headers)
    assert r.status_code == 200
    assert any(e["id"] == exam_id for e in r.json())

    print("\nTesting GET /exams/{id}...")
    r = requests.get(f"{BASE_URL}/exams/{exam_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Blockchain Architecture Design - Internal Assessment 1"

    print("\nTesting GET /subjects/{id}/exams...")
    r = requests.get(f"{BASE_URL}/subjects/{subject_id}/exams")
    assert r.status_code == 200
    assert any(e["id"] == exam_id for e in r.json())

    print("\nAll Phase 6 Tests Passed successfully!")

if __name__ == "__main__":
    run_phase6_tests()
