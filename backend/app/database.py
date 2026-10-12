from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Attempt to create the engine and session factory
try:
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    raise RuntimeError(
        "Failed to configure database. Please ensure PostgreSQL is running, "
        "and the DATABASE_URL in your .env file is correct. "
        f"Original error: {str(e)}"
    )

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
