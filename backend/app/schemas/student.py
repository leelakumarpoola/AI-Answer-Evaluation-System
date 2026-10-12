from pydantic import BaseModel, EmailStr, field_validator
import re
from datetime import datetime

class StudentBase(BaseModel):
    name: str
    roll_number: str
    email: EmailStr
    department: str = "Computer Science and Engineering"
    year: int = 4
    section: str = "3"

class StudentCreate(StudentBase):
    @field_validator('roll_number')
    @classmethod
    def validate_roll_number(cls, v: str) -> str:
        if not re.match(r"^23BCE\d{4}$", v):
            raise ValueError('Registration number must follow the format 23BCE####')
        return v
        
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        v_str = str(v)
        if not v_str.endswith("2023@vitstudent.vit.ac.in"):
            raise ValueError('Email must end with 2023@vitstudent.vit.ac.in')
        if not v_str.islower():
            raise ValueError('Email must be lowercase')
        return v_str

class StudentResponse(StudentBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
