from app.database import SessionLocal
from app.models.student import Student
from app.models.professor import Professor
from app.models.subject import Subject
from app.models.exam import Exam

db = SessionLocal()
students = db.query(Student).all()
print(f"Total students: {len(students)}")
names = [s.name for s in students if s.name in ["Leela Kumar P", "Kowshik P", "Sai Yashwanth K"]]
print(f"Found specific students: {names}")
print(f"Max roll number: {max([s.roll_number for s in students]) if students else 'None'}")

prof = db.query(Professor).first()
if prof: print(f"Prof: {prof.name}, {prof.department}")

subj = db.query(Subject).first()
if subj: print(f"Subject: {subj.name}, {subj.code}")

exam = db.query(Exam).first()
if exam: print(f"Exam: {exam.name}")
