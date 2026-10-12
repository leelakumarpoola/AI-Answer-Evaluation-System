from app.database import engine, Base
from sqlalchemy import text
from app.models.model_answer import ModelAnswer

def migrate():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE questions ALTER COLUMN question_number TYPE VARCHAR;"))
            conn.commit()
            print("Successfully migrated question_number to String.")
        except Exception as e:
            print(f"Error migrating (may already be migrated): {e}")

    Base.metadata.create_all(engine)
    print("Database tables updated.")

if __name__ == "__main__":
    migrate()
