from app.database import SessionLocal
from sqlalchemy import text
from app.models.student import Student

db = SessionLocal()
tables = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")).fetchall()
print("Tables:", [t[0] for t in tables])

if "students" in [t[0] for t in tables]:
    count = db.query(Student).count()
    print("Students count:", count)
else:
    print("No students table yet.")
