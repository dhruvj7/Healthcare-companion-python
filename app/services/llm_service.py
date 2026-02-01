# app/services/llm_service.py
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings

def get_llm():
    """Get configured Gemini LLM instance"""
    return ChatGoogleGenerativeAI(
        model=settings.LLM_MODEL,           # "gemini-2.5-flash"
        temperature=settings.LLM_TEMPERATURE, # 0.3 (low = more deterministic)
        google_api_key=settings.GOOGLE_API_KEY,
        max_output_tokens=settings.LLM_MAX_TOKENS  # 2048
    )