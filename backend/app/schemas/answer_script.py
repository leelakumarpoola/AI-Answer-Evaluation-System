from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class AnswerScriptResponse(BaseModel):
    id: int
    student_id: int
    exam_id: int
    file_name: str
    file_size: Optional[int]
    upload_status: str
    processing_status: str
    ocr_status: str
    page_count: int
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class OCRPageResponse(BaseModel):
    page_number: int
    text: Optional[str]
    ocr_status: str
    ocr_confidence: Optional[float]

class AnswerScriptOCRResponse(BaseModel):
    answer_script_id: int
    student_id: int
    exam_id: int
    status: str
    pages: List[OCRPageResponse]
