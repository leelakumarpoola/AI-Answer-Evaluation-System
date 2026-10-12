from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE rubric_evaluations (id SERIAL PRIMARY KEY, evaluation_id INTEGER NOT NULL REFERENCES evaluations(id), rubric_id INTEGER NOT NULL REFERENCES rubrics(id), evidence_score FLOAT NOT NULL, suggested_marks FLOAT NOT NULL, reason VARCHAR, created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP)"))
        conn.commit()
        print("Table rubric_evaluations created.")
except Exception as e:
    print(f"Migration error (already exists?): {e}")
