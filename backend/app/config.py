from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/answer_evaluation_db"
    secret_key: str = "change-this-development-secret"

    # Tesseract OCR path (auto-detected if not set)
    tesseract_cmd: Optional[str] = None

    # TrOCR optional backend (disabled by default — set to "true" to enable)
    trocr_enabled: str = "false"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
