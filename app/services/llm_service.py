from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class FallbackGeminiLLM:
    """
    Gemini LLM wrapper with automatic fallback models
    """

    def __init__(self):
        self.models = [
            settings.PRIMARY_LLM_MODEL,
            *settings.FALLBACK_LLM_MODELS
        ]

    def invoke(self, prompt: str):
        last_error = None

        for model_name in self.models:
            try:
                logger.info(f"Trying Gemini model: {model_name}")

                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=settings.LLM_TEMPERATURE,
                    google_api_key=settings.GOOGLE_API_KEY,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                )

                response = llm.invoke(prompt)

                if response and response.content:
                    logger.info(f"Gemini success with model: {model_name}")
                    return response

            except Exception as e:
                logger.warning(
                    f"Gemini model failed [{model_name}]: {e}"
                )
                last_error = e
                continue

        logger.error("All Gemini models exhausted")
        raise last_error or RuntimeError("All LLM models failed")


def get_llm():
    """
    Returns a Gemini LLM with automatic fallback.
    Call site remains unchanged.
    """
    if not settings.ENABLE_LLM:
        raise RuntimeError("LLM disabled via config")

    return FallbackGeminiLLM()
