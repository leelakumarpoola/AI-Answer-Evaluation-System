# AI-Powered Answer Script Evaluation System

## Project Description
The **AI-Powered Answer Script Evaluation System** is a comprehensive full-stack solution designed to streamline the academic grading process. It empowers professors to upload student answer scripts, securely extract responses via OCR, and evaluate them automatically against structured model answers and rubrics. 

This repository contains the **Final Backend** API, equipped with advanced semantic similarity checks (using `sentence-transformers`), multi-modal rubric-based AI scoring, detailed report generation, and robust role-based access control (RBAC).

## Technology Stack
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL (with SQLAlchemy ORM)
- **Authentication:** JWT Bearer tokens
- **PDF Processing:** PyMuPDF (`fitz`)
- **OCR:** Tesseract (`pytesseract`) + OpenCV/Pillow
- **AI / NLP:** `sentence-transformers` (all-MiniLM-L6-v2), PyTorch, scikit-learn
- **Data Manipulation:** NumPy, Pandas (where applicable)

## Backend Structure
The project adopts a modular, domain-driven structure:
```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── config.py          # Environment settings
│   ├── database.py        # Database engine & session
│   ├── models/            # SQLAlchemy database schemas
│   ├── schemas/           # Pydantic validation schemas
│   ├── routers/           # API routes (auth, documents, etc.)
│   ├── services/          # Core business & AI logic
│   └── utils/             # Helper utilities (auth hashing, etc.)
│
├── uploads/               # Securely isolated document storage
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment template
├── .gitignore             # Version control exclusions
└── README.md              # Project documentation
```

## Setup Instructions

### 1. Python Environment Setup
Open your terminal in the `backend` directory and run:
```bash
python -m venv venv
```
Activate virtual environment:
* Windows: `venv\Scripts\activate`
* Mac/Linux: `source venv/bin/activate`

### 2. Dependencies & OCR Setup
1. **Install Tesseract OCR:**
   - **Windows:** Download from [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki). Add `TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"` to `.env`.
   - **Linux:** `sudo apt-get install tesseract-ocr`
   - **Mac:** `brew install tesseract`

2. **Install Python Packages:**
   ```bash
   pip install -r requirements.txt
   ```

### 3. PostgreSQL Setup
1. Install PostgreSQL and create the database:
   ```sql
   CREATE DATABASE answer_evaluation_db;
   ```
2. SQLAlchemy will automatically structure the application tables when the application starts.

### 4. Configuration
Duplicate `.env.example` to `.env` and fill in the values:
```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/answer_evaluation_db
SECRET_KEY=change-this-production-secret
TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Running the Backend
Start the Uvicorn server:
```bash
uvicorn app.main:app --reload --port 8000
```
Check the server is running by navigating to `http://127.0.0.1:8000/`.

## Swagger API Documentation
Interactive documentation for all available endpoints can be found at:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Authentication
- **Professor Login:** `POST /auth/professor/login`
- **Student Login:** `POST /auth/student/login`
The system strictly utilizes **Bearer JWT**. You must attach the token to the `Authorization` header for protected endpoints. 

## Processing Workflow
The complete end-to-end pipeline operates as follows:
1. **Setup:** Professor registers, creates a Subject, and sets up an Exam.
2. **Master Documents:** Professor uploads the Question Paper, Model Answer, and Marks Rubric.
3. **Extraction:** The backend runs OCR, parsing structured questions, model answers, and rubric metadata.
4. **Student Submission:** Professor uploads Student Answer Scripts.
5. **Student OCR:** Scripts are digitized and mapped back to the extracted exam questions.
6. **Semantic Similarity:** `SBERT` matches the structural meaning between student and model answers.
7. **Rubric Evaluation:** AI cross-references the student answer, the rubric limits, and the similarity score to derive an **AI Suggested Mark**.
8. **AI Feedback:** Detailed feedback is produced per question.
9. **Professor Review:** Professor reviews AI marks and locks in their **Final Mark** via an explicit **Approval** state. 
10. **Results & Analytics:** Verified marks manifest into dynamic JSON reports containing robust class metrics.

## API Overview
* `/auth/*`: Login and registration routes.
* `/students/*`: Student records and role validation.
* `/subjects/*`: Subject cataloging.
* `/exams/*`: Exam creation, ownership validation.
* `/documents/*`: Secure file upload and mapping.
* `/answer-scripts/*`: Student answers ingestion and processing.
* `/evaluations/*`: Reviewing and updating AI results to Final Approval constraints.
* `/results/*`: End-user readouts of official marks.
* `/reports/*`: Aggregate professor-level distribution analytics.

## Testing
Comprehensive regression testing logic is isolated in local `test_*.py` files. To validate logic, ensure your virtual environment is active and run:
```bash
python test_auth.py
python test_phase14.py
python test_phase15.py
python test_phase16.py
python test_phase17.py
python test_phase18.py
```
*Note: A clean test run will typically spawn isolated, one-off test subjects and students in the local database to assure side-effect-free validations.*
