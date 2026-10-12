from pydantic import BaseModel, EmailStr
from typing import Optional

class ProfessorRegister(BaseModel):
    name: str
    email: EmailStr
    department: str
    password: str

class ProfessorLogin(BaseModel):
    email: EmailStr
    password: str

class StudentRegister(BaseModel):
    roll_number: str
    email: EmailStr
    password: str

class StudentLogin(BaseModel):
    identifier: str  # Can be email or roll_number
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class CurrentUser(BaseModel):
    id: int
    email: EmailStr
    role: str
    name: Optional[str] = None
