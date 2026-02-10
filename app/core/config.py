# app/core/config.py

from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # =========================
    # Application
    # =========================
    APP_NAME: str = "Healthcare AI Service"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # =========================
    # CORS
    # =========================
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8080",
        "http://localhost:3000",
        "http://localhost:4200",
    ]

    # =========================
    # AI / LLM Configuration
    # =========================
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # Primary LLM
    PRIMARY_LLM_MODEL: str = os.getenv(
        "PRIMARY_LLM_MODEL", "gemini-2.5-flash"
    )

    # Fallback LLMs (comma separated)
    FALLBACK_LLM_MODELS: list[str] = [
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash"
        # "gemini-2.0-pro",
    ]

    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # Feature flags
    ENABLE_LLM: bool = os.getenv("ENABLE_LLM", "true").lower() == "true"

    # =========================
    # Rate Limiting
    # =========================
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # =========================
    # Logging
    # =========================
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # =========================
    # Database
    # =========================
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # =========================
    # SMTP / Email
    # =========================
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
