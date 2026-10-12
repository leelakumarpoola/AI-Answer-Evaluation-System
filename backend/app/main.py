from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import engine, get_db, Base
from app import models

# Create all tables in the database
Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Answer Evaluation System API",
    description="Backend for the AI-Powered Answer Script Evaluation System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:3000",
        "https://ai-evaluation-portal.local"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import students, auth, subjects, exams, documents, answer_scripts, evaluations, results, reports
app.include_router(students.router)
app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(exams.router)
app.include_router(documents.router)
app.include_router(answer_scripts.router)
app.include_router(evaluations.router)
app.include_router(results.router)
app.include_router(reports.router)

@app.get("/")
def read_root():
    return {"message": "AI Answer Evaluation System Backend Running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/db-test")
def test_db_connection(db: Session = Depends(get_db)):
    try:
        # Attempt to execute a simple query to verify the connection
        result = db.execute(text("SELECT 1")).scalar()
        if result == 1:
            return {
                "status": "success",
                "database": "PostgreSQL",
                "message": "Database connection successful"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Database connection test returned unexpected result."
            )
    except Exception as e:
        import logging
        logging.error(f"Database connection error: {str(e)}")
        # Do not expose sensitive information like the connection string or password
        raise HTTPException(
            status_code=500,
            detail="Database connection failed. Ensure PostgreSQL is running, the database exists, and credentials are correct."
        )

@app.get("/db-tables")
def get_db_tables(db: Session = Depends(get_db)):
    try:
        # Query PostgreSQL specific table for table names
        result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
        tables = [row[0] for row in result]
        return {
            "status": "success",
            "tables": tables
        }
    except Exception as e:
        import logging
        logging.error(f"Error fetching tables: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch tables.")

