import requests

BASE_URL = "http://127.0.0.1:8000"

def test_get_root():
    r = requests.get(f"{BASE_URL}/")
    print("GET / :", r.status_code, r.json())

def test_get_health():
    r = requests.get(f"{BASE_URL}/health")
    print("GET /health :", r.status_code, r.json())

def test_get_db_test():
    r = requests.get(f"{BASE_URL}/db-test")
    print("GET /db-test :", r.status_code, r.json())

def test_get_students():
    r = requests.get(f"{BASE_URL}/students/")
    print("GET /students/ status:", r.status_code)
    data = r.json()
    print("Total students:", len(data))
    if len(data) > 0:
        print("First student:", data[0]['name'])

def test_get_student_id(id):
    r = requests.get(f"{BASE_URL}/students/{id}")
    print(f"GET /students/{id} status:", r.status_code)
    if r.status_code == 200:
        print("Student data:", r.json()['name'])

def test_post_student():
    student_data = {
        "name": "Test Student",
        "roll_number": "23BCE0031",
        "email": "teststudent2023@vitstudent.vit.ac.in",
        "department": "Computer Science and Engineering",
        "year": 4,
        "section": "3"
    }
    r = requests.post(f"{BASE_URL}/students/", json=student_data)
    print("POST /students/ (student 31) status:", r.status_code)
    print("Response:", r.json())
    return r.json().get('id') if r.status_code == 201 else None

def test_duplicate_roll_number():
    student_data = {
        "name": "Duplicate Roll",
        "roll_number": "23BCE0031",  # Same as above
        "email": "dup12023@vitstudent.vit.ac.in",
        "department": "CSE",
        "year": 4,
        "section": "3"
    }
    r = requests.post(f"{BASE_URL}/students/", json=student_data)
    print("POST /students/ (Duplicate Roll) status:", r.status_code)
    print("Response:", r.json())

def test_duplicate_email():
    student_data = {
        "name": "Duplicate Email",
        "roll_number": "23BCE0032",
        "email": "teststudent2023@vitstudent.vit.ac.in",  # Same as above
        "department": "CSE",
        "year": 4,
        "section": "3"
    }
    r = requests.post(f"{BASE_URL}/students/", json=student_data)
    print("POST /students/ (Duplicate Email) status:", r.status_code)
    print("Response:", r.json())

def test_invalid_roll_number():
    student_data = {
        "name": "Invalid Roll",
        "roll_number": "23BCE123",  # Invalid format
        "email": "invalid2023@vitstudent.vit.ac.in",
        "department": "CSE",
        "year": 4,
        "section": "3"
    }
    r = requests.post(f"{BASE_URL}/students/", json=student_data)
    print("POST /students/ (Invalid Roll) status:", r.status_code)
    print("Response:", r.json())

if __name__ == "__main__":
    test_get_root()
    test_get_health()
    test_get_db_test()
    test_get_students()
    test_get_student_id(1)
    
    # Test adding 31st student
    new_id = test_post_student()
    
    if new_id:
        test_duplicate_roll_number()
        test_duplicate_email()
        test_invalid_roll_number()
        
        # Cleanup
        print("Cleaning up test student 31...")
        from sqlalchemy.orm import Session
        import sys, os
        sys.path.append(os.path.abspath('.'))
        from app.database import SessionLocal
        from app.models.student import Student
        db = SessionLocal()
        db.query(Student).filter(Student.id == new_id).delete()
        db.commit()
        db.close()
        print("Cleanup done.")
