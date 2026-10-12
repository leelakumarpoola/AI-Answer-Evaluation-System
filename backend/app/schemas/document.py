from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ExamDocumentBase(BaseModel):
    document_type: str
    file_name: str
    file_type: str
    file_size: int

class ExamDocumentResponse(ExamDocumentBase):
    id: int
    exam_id: int
    upload_status: str
    processing_status: str
    page_count: int
    processed_page_count: int
    processing_error: Optional[str] = None
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class ProcessedPageResponse(BaseModel):
    page_number: int
    file_name: str
