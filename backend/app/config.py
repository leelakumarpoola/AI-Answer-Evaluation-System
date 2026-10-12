from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/answer_evaluation_db"
    secret_key: str = "change-this-development-secret"
    
    class Config:
        env_file = ".env"

settings = Settings()
