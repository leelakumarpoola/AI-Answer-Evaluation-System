# Phase 14 Security & Hardcoding Audit Final Report

## 1. Overview
The final milestone for Phase 14 involved implementing a strict security audit across all existing routers to completely remove hard-coded user logic and enforce proper JWT ownership checks for all endpoints.

## 2. Hardcoded Values Removed
All development hardcodes, such as `professor_id=1`, `student_id=1`, and mock strings like `"BCSE329L"`, have been completely removed from application logic. The seed data (`23BCE0001`, `Prof Rahul Tripati`) is preserved strictly as database records.

## 3. Architecture Validated
- `app/routers/auth.py`: Provides strict JWTs with `role` and `sub` correctly stored.
- `app/routers/students.py`: Verified `GET /students/{id}` blocks students from accessing IDs that do not match their own JWT token.
- `app/routers/subjects.py`: Required professor JWT for creation, and authenticated user for retrieval.
- `app/routers/exams.py`: Enforced that only the professor who created the exam can retrieve or modify it (`exam.professor_id == current_user.id`).
- `app/routers/documents.py`: Locked down document uploads and retrieval to only the owning professor.
- `app/routers/answer_scripts.py`: Safely enforces that students cannot trigger `/rubric-evaluation` (returns 403 Forbidden).

## 4. Testing Results
We ran the explicitly requested test suite (10 security checks plus all Phase 14 functional tests).
- **TEST 1-2**: Valid Professor & Student logins generate valid `Bearer` tokens.
- **TEST 3**: Invalid passwords return `401 Unauthorized`.
- **TEST 4-6**: Missing, malformed, and expired JWTs properly result in `401 Unauthorized`.
- **TEST 7**: Student attempts to trigger rubric evaluation blocked (`403 Forbidden`).
- **TEST 8**: Professor successfully evaluates their own answer script (`200 OK`).
- **TEST 9**: Professor attempts to evaluate another professor's answer script blocked (`403 Forbidden`).
- **TEST 10**: Student accesses another student's evaluation endpoint blocked (`403 Forbidden`).

**All security and functionality tests passed successfully.**
