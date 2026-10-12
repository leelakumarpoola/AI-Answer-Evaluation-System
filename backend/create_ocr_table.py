from app.database import engine, Base
from app.models.ocr_result import OCRResult

def create_table():
    Base.metadata.create_all(engine)
    print("OCR table created.")

if __name__ == "__main__":
    create_table()
