import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app import models
from app.utils.security import create_access_token

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture(scope="module")
def valid_script(db_session):
    """Returns an answer script whose physical PDF file exists on disk."""
    scripts = db_session.query(models.AnswerScript).all()
    real_script = next((s for s in scripts if s.file_path and os.path.exists(s.file_path)), None)
    assert real_script is not None, "At least one answer script with existing PDF must exist"
    return real_script

def test_unauthenticated_pdf_access_blocked(client, valid_script):
    """Verify that unauthenticated requests to view answer sheet PDF are denied with 401."""
    res = client.get(f"/answer-scripts/{valid_script.id}/pdf")
    assert res.status_code == 401
    assert "token" in res.json().get("detail", "").lower()

def test_view_answer_script_pdf_by_owning_professor(client, db_session, valid_script):
    """Verify that the owning professor can view the original student answer sheet PDF."""
    exam = db_session.query(models.Exam).filter(models.Exam.id == valid_script.exam_id).first()
    assert exam is not None
    
    prof_token = create_access_token({"sub": str(exam.professor_id), "role": "professor"})
    headers = {"Authorization": f"Bearer {prof_token}"}
    
    res = client.get(f"/answer-scripts/{valid_script.id}/pdf", headers=headers)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert "inline" in res.headers.get("content-disposition", "")
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) == os.path.getsize(valid_script.file_path)

def test_view_pdf_via_exam_and_student_id(client, db_session, valid_script):
    """Verify endpoint GET /exams/{exam_id}/students/{student_id}/answer-script/pdf."""
    exam = db_session.query(models.Exam).filter(models.Exam.id == valid_script.exam_id).first()
    prof_token = create_access_token({"sub": str(exam.professor_id), "role": "professor"})
    
    res = client.get(
        f"/exams/{valid_script.exam_id}/students/{valid_script.student_id}/answer-script/pdf",
        headers={"Authorization": f"Bearer {prof_token}"}
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")

def test_view_pdf_via_query_token(client, db_session, valid_script):
    """Verify that opening the PDF in a new browser tab with ?token=... query parameter authenticates properly."""
    exam = db_session.query(models.Exam).filter(models.Exam.id == valid_script.exam_id).first()
    prof_token = create_access_token({"sub": str(exam.professor_id), "role": "professor"})
    
    res = client.get(f"/answer-scripts/{valid_script.id}/pdf?token={prof_token}")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF-")

def test_view_pdf_forbidden_for_other_professor(client, db_session, valid_script):
    """Verify that a professor who does not own the exam cannot access another professor's student answer sheet."""
    exam = db_session.query(models.Exam).filter(models.Exam.id == valid_script.exam_id).first()
    
    # Find a professor who is NOT the owner
    other_prof = db_session.query(models.Professor).filter(models.Professor.id != exam.professor_id).first()
    if other_prof:
        unauth_token = create_access_token({"sub": str(other_prof.id), "role": "professor"})
        res = client.get(f"/answer-scripts/{valid_script.id}/pdf", headers={"Authorization": f"Bearer {unauth_token}"})
        assert res.status_code == 403
        assert "not own" in res.json().get("detail", "").lower()

def test_view_pdf_by_student_owner_and_other_student(client, db_session, valid_script):
    """Verify student authorization: allowed for own script, forbidden for another student's script."""
    # Owning student
    owner_token = create_access_token({"sub": str(valid_script.student_id), "role": "student"})
    res_owner = client.get(f"/answer-scripts/{valid_script.id}/pdf", headers={"Authorization": f"Bearer {owner_token}"})
    assert res_owner.status_code == 200
    assert res_owner.headers["content-type"] == "application/pdf"
    
    # Other student
    other_student = db_session.query(models.Student).filter(models.Student.id != valid_script.student_id).first()
    if other_student:
        other_token = create_access_token({"sub": str(other_student.id), "role": "student"})
        res_other = client.get(f"/answer-scripts/{valid_script.id}/pdf", headers={"Authorization": f"Bearer {other_token}"})
        assert res_other.status_code == 403

def test_missing_physical_file_returns_404(client, db_session):
    """Verify that a script whose physical file is missing from disk returns 404."""
    dummy_script = db_session.query(models.AnswerScript).filter(
        models.AnswerScript.file_path.ilike("%dummy%")
    ).first()
    if dummy_script:
        exam = db_session.query(models.Exam).filter(models.Exam.id == dummy_script.exam_id).first()
        if exam:
            prof_token = create_access_token({"sub": str(exam.professor_id), "role": "professor"})
            res = client.get(f"/answer-scripts/{dummy_script.id}/pdf", headers={"Authorization": f"Bearer {prof_token}"})
            assert res.status_code == 404
            assert "not found" in res.json().get("detail", "").lower()

def test_nonexistent_answer_script_returns_404(client, db_session):
    """Verify 404 for invalid answer script id."""
    prof = db_session.query(models.Professor).first()
    prof_token = create_access_token({"sub": str(prof.id), "role": "professor"})
    res = client.get("/answer-scripts/999999/pdf", headers={"Authorization": f"Bearer {prof_token}"})
    assert res.status_code == 404

def test_full_review_package_includes_answer_script_metadata(client, db_session):
    """Verify that get_evaluation_review returns answer_script metadata."""
    eval_record = db_session.query(models.Evaluation).first()
    if eval_record:
        script = eval_record.student_answer.answer_script
        exam = script.exam
        prof_token = create_access_token({"sub": str(exam.professor_id), "role": "professor"})
        
        res = client.get(f"/evaluations/{eval_record.id}/review", headers={"Authorization": f"Bearer {prof_token}"})
        assert res.status_code == 200
        data = res.json()
        assert "answer_script_id" in data
        assert data["answer_script_id"] == script.id
        assert "answer_script_file_name" in data
