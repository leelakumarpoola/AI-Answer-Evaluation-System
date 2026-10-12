import sqlite3
import psycopg2
import os

from sqlalchemy import create_engine
from app.database import engine
from sqlalchemy import text

def migrate_phase12():
    print(f"Applying migration via SQLAlchemy")
    with engine.connect() as conn:
        try:
            # Alter table student_answers
            conn.execute(text("ALTER TABLE student_answers DROP COLUMN IF EXISTS page_number;"))
            conn.execute(text("ALTER TABLE student_answers ADD COLUMN IF NOT EXISTS start_page INTEGER;"))
            conn.execute(text("ALTER TABLE student_answers ADD COLUMN IF NOT EXISTS end_page INTEGER;"))
            conn.execute(text("ALTER TABLE student_answers ADD COLUMN IF NOT EXISTS answer_status VARCHAR DEFAULT 'detected';"))
            conn.commit()
            print("Migration for Phase 12 applied successfully.")
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_phase12()
