from app.database import engine, Base
from sqlalchemy import text
from app.models.answer_script_page import AnswerScriptPage

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE answer_scripts ADD COLUMN file_size INTEGER;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE answer_scripts ADD COLUMN processing_status VARCHAR DEFAULT 'pending';"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE answer_scripts ADD COLUMN ocr_status VARCHAR DEFAULT 'pending';"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE answer_scripts ADD COLUMN page_count INTEGER DEFAULT 0;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE answer_scripts ADD COLUMN processing_error VARCHAR;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE answer_scripts ADD COLUMN processed_at TIMESTAMP WITH TIME ZONE;"))
        except Exception: pass
        conn.commit()
        print("Successfully migrated answer_scripts.")

    Base.metadata.create_all(engine)
    print("Database tables updated.")

if __name__ == "__main__":
    migrate()
