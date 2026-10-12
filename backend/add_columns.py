from app.database import engine
from sqlalchemy import text
with engine.begin() as con:
    try:
        con.execute(text("ALTER TABLE exam_documents ADD COLUMN processing_status VARCHAR DEFAULT 'uploaded'"))
        con.execute(text("ALTER TABLE exam_documents ADD COLUMN page_count INTEGER DEFAULT 0"))
        con.execute(text("ALTER TABLE exam_documents ADD COLUMN processed_page_count INTEGER DEFAULT 0"))
        con.execute(text("ALTER TABLE exam_documents ADD COLUMN processing_error VARCHAR NULL"))
        con.execute(text("ALTER TABLE exam_documents ADD COLUMN processed_at TIMESTAMP WITH TIME ZONE NULL"))
        print("Success")
    except Exception as e:
        print("Error:", e)
