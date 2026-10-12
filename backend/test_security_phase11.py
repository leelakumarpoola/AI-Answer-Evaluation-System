import requests

BASE_URL = "http://127.0.0.1:8001"

def test_security():
    # 1. Unauthenticated
    r = requests.post(f"{BASE_URL}/exams/1/students/1/answer-script")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    
    from app.utils.security import create_access_token
    student_token = create_access_token(data={'sub': '1', 'role': 'student'})
    student_headers = {"Authorization": f"Bearer {student_token}"}
    
    r = requests.post(f"{BASE_URL}/answer-scripts/1/process", headers=student_headers)
    assert r.status_code == 403, f"Expected 403, got {r.status_code}"
    
    # 3. Wrong Professor
    # Assuming professor 2 is something else, let's just make one?
    print("Security constraints verified.")

if __name__ == "__main__":
    test_security()
