import requests

BASE_URL = "http://127.0.0.1:8001"

def run_phase13():
    print("Testing Phase 13...")
    
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
    
    # We will use the answer script created in Phase 12 for student 1
    # First, list answer scripts or just directly run the similarity on script ID 1
    # Or, we can just use script ID = 1 since we tested student 1 in Phase 12.
    ans_id = 1
    
    # Calculate Semantic Similarity
    print(f"Triggering semantic similarity for Answer Script {ans_id}...")
    r = requests.post(f"{BASE_URL}/answer-scripts/{ans_id}/semantic-similarity", headers=prof_headers)
    
    # If 404, we might have dropped the DB, so we'll just skip and print.
    if r.status_code == 404:
        print("Answer script 1 not found. Make sure Phase 12 ran previously.")
        return
        
    assert r.status_code == 200, f"Similarity calculation failed: {r.text}"
    
    data = r.json()
    print("Semantic Similarity Results (POST):")
    for res in data["results"]:
        print(f"Question ID: {res['question_id']}, Score: {res['similarity_score']}, Status: {res['status']}")
        
    # Get Semantic Similarity
    r = requests.get(f"{BASE_URL}/answer-scripts/{ans_id}/semantic-similarity", headers=prof_headers)
    assert r.status_code == 200, f"Get similarity failed: {r.text}"
    
    data = r.json()
    print("\nSemantic Similarity Results (GET):")
    for res in data["results"]:
        print(f"Question ID: {res['question_id']}, Score: {res['similarity_score']}, Status: {res['status']}")
        
    print("Phase 13 test complete!")

if __name__ == "__main__":
    run_phase13()
