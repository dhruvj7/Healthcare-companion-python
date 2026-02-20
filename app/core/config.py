# app/core/config.py

from pydantic_settings import BaseSettings
from typing import ClassVar, List
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
        "https://care-navigator.netlify.app"
    ]
    
    # AI/LLM Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    # =========================
    # AI / LLM Configuration
    # =========================
    GOOGLE_API_KEY: str = "AIzaSyBdsY7vus5Wg2trE0DyfdLjR8KyMx3ZALY"

    # Primary LLM
    PRIMARY_LLM_MODEL: str = os.getenv(
        "PRIMARY_LLM_MODEL", "gemini-2.5-flash"
    )
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "gsk_9enrgSYnIvCDpKTvdCFpWGdyb3FY2XhkSkQtkX6IqoM")
    GROQ_MODELS: List[str] = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]

   


    # Fallback LLMs (comma separated)
    FALLBACK_LLM_MODELS: list[str] = [
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash"
        # "gemini-2.0-pro",
    ]

    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    # Lower default to reduce Gemini quota usage (512–1024 is enough for most responses)
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))

    # Allow Groq as fallback when Gemini quota is exhausted (set to "false" to disable Groq entirely)
    # Note: Groq responses may be lower quality, so Gemini is always tried first
    LLM_USE_GROQ_FIRST: bool = os.getenv("LLM_USE_GROQ_FIRST", "false").lower() == "true"

    # Max LLM-backed chat requests per session per minute (reduces quota exhaustion)
    LLM_REQUESTS_PER_SESSION_PER_MINUTE: int = int(os.getenv("LLM_REQUESTS_PER_SESSION_PER_MINUTE", "15"))

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
    SMTP_HOST: str= "smtp.gmail.com"
    SMTP_PORT: int=587
    SMTP_USERNAME: str= "igironbat@gmail.com"
    SMTP_PASSWORD: str= "cfsa macq trho vafy"
    SMTP_FROM_EMAIL: str="igironbat@gmail.com"
  


    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
