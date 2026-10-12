from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.utils.security import ALGORITHM
from app.models.professor import Professor
from app.models.student import Student
from app.schemas.auth import CurrentUser

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> CurrentUser:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        role: str = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if role == "professor":
        user = db.query(Professor).filter(Professor.id == user_id).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return CurrentUser(id=user.id, email=user.email, role=role, name=user.name)
        
    elif role == "student":
        user = db.query(Student).filter(Student.id == user_id).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return CurrentUser(id=user.id, email=user.email, role=role, name=user.name)
    else:
        raise credentials_exception

def require_professor(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "professor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Professor role required."
        )
    return current_user

def require_student(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Student role required."
        )
    return current_user
