from app.database import SessionLocal
from app.models.professor import Professor
db = SessionLocal()
profs = db.query(Professor).all()
for p in profs:
    print(p.name, p.email, p.department)
