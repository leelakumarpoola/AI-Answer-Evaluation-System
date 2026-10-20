from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re

class SubjectBase(BaseModel):
    name: str
    code: str
    department: str
    class_section: Optional[str] = None

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        if not re.match(r"^BCSE[0-9]{3}L$", v):
            raise ValueError('Course code must follow the format ^BCSE[0-9]{3}L$')
        return v

class SubjectCreate(SubjectBase):
    pass

class SubjectResponse(SubjectBase):
    id: int
    professor_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
