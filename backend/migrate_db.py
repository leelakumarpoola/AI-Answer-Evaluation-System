from app.database import engine
from sqlalchemy import text

with engine.begin() as con:
    try:
        con.execute(text('ALTER TABLE students ADD COLUMN password_hash VARCHAR NULL;'))
        con.execute(text('ALTER TABLE students ADD COLUMN is_active BOOLEAN DEFAULT TRUE;'))
    except Exception as e:
        print("Student alter error:", e)
        
    try:
        con.execute(text('ALTER TABLE professors ADD COLUMN password_hash VARCHAR NULL;'))
        con.execute(text('ALTER TABLE professors ADD COLUMN is_active BOOLEAN DEFAULT TRUE;'))
    except Exception as e:
        print("Professor alter error:", e)

print("Migration completed.")
