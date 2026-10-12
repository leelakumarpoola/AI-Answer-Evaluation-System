import os
import sys

# Ensure the app module can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from app.database import engine, get_db, SessionLocal
from app.models.student import Student

NAMES = [
    "Leela Kumar P",
    "Kowshik P",
    "Sai Yashwanth K",
    "Aarav Patel",
    "Aditi Sharma",
    "Arjun Singh",
    "Diya Reddy",
    "Ishaan Gupta",
    "Kavya Nair",
    "Pranav Desai",
    "Riya Verma",
    "Rohan Mishra",
    "Sanya Iyer",
    "Vihaan Joshi",
    "Zara Khan",
    "Advik Rao",
    "Ananya Menon",
    "Dhruv Chawla",
    "Nidhi Pillai",
    "Kabir Das",
    "Meera Bhatt",
    "Rudra Nambiar",
    "Tara Chatterjee",
    "Vivaan Dubey",
    "Anika Kulkarni",
    "Aryan Soni",
    "Kiara Ahuja",
    "Reyansh Bhatia",
    "Sia Kapoor",
    "Yug Agarwal"
]

def generate_email(name: str) -> str:
    # Remove spaces and convert to lowercase
    base = name.replace(" ", "").lower()
    return f"{base}2023@vitstudent.vit.ac.in"

def seed_students():
    db: Session = SessionLocal()
    try:
        print("Starting seed process...")
        added_count = 0
        for i, name in enumerate(NAMES, start=1):
            roll_number = f"23BCE{i:04d}"
            email = generate_email(name)
            
            # Check if student already exists by roll_number or email
            existing = db.query(Student).filter(
                (Student.roll_number == roll_number) | (Student.email == email)
            ).first()
            
            if existing:
                print(f"Student {roll_number} ({name}) already exists. Skipping.")
                continue
            
            student = Student(
                name=name,
                roll_number=roll_number,
                email=email,
                department="Computer Science and Engineering",
                year=4,
                section="3"
            )
            db.add(student)
            added_count += 1
            
        db.commit()
        print(f"Successfully seeded {added_count} new students.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding students: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_students()
