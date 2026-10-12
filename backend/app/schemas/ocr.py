from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OCRPageResponse(BaseModel):
    page_number: int
    text: Optional[str]
    ocr_status: str
    ocr_confidence: Optional[float]
    
    model_config = {"from_attributes": True}

class OCRDocumentResponse(BaseModel):
    document_id: int
    status: str
    pages: List[OCRPageResponse]
    
    model_config = {"from_attributes": True}
