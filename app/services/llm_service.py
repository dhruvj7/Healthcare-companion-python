from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from google.api_core.exceptions import ResourceExhausted
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


class FallbackGeminiLLM(Runnable):
    """
    Multi-provider LLM router:
    1. Gemini (primary + fallback)
    2. Groq (free cross-provider fallback)
    """

    def __init__(self):
        self.gemini_models = [
            settings.PRIMARY_LLM_MODEL,
            *settings.FALLBACK_LLM_MODELS,
        ]

        self.groq_models = settings.GROQ_MODELS

    # --------------------------------------------------
    # 🔥 ASYNC
    # --------------------------------------------------
    async def ainvoke(self, prompt, config=None):
        last_error = None

        # =========================
        # 1️⃣ Gemini models
        # =========================
        for model_name in self.gemini_models:
            try:
                logger.info(f"Trying Gemini model: {model_name}")

                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=settings.LLM_TEMPERATURE,
                    google_api_key=settings.GOOGLE_API_KEY,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                )

                response = await llm.ainvoke(prompt, config=config)

                if response and response.content:
                    logger.info(f"Gemini success: {model_name}")
                    return response

            except ResourceExhausted as e:
                logger.warning(f"Gemini quota exhausted [{model_name}]")
                last_error = e
                continue

            except Exception as e:
                logger.warning(f"Gemini failed [{model_name}]: {e}")
                last_error = e
                continue

        # =========================
        # 2️⃣ Groq models (FALLBACK ONLY - lower quality, use only if Gemini fails)
        # =========================
        # Only use Groq if explicitly enabled AND Gemini has failed
        if settings.LLM_USE_GROQ_FIRST:  # This flag now means "allow Groq as fallback"
            logger.warning("Gemini exhausted, falling back to Groq (lower quality responses)")
            for model_name in self.groq_models:
                try:
                    logger.info(f"Trying Groq fallback: {model_name}")
                    llm = ChatGroq(
                        model=model_name,
                        api_key=settings.GROQ_API_KEY,
                        temperature=settings.LLM_TEMPERATURE,
                        max_tokens=settings.LLM_MAX_TOKENS,
                    )
                    response = await llm.ainvoke(prompt, config=config)
                    if response and response.content:
                        logger.warning(f"Groq fallback used (may have lower quality): {model_name}")
                        return response
                except Exception as e:
                    logger.warning(f"Groq failed [{model_name}]: {e}")
                    last_error = e
                    continue

        logger.error("All LLM providers exhausted")
        raise last_error or RuntimeError("All LLMs failed")

    # --------------------------------------------------
    # 🔥 SYNC
    # --------------------------------------------------
    def invoke(self, prompt, config=None):
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot use sync invoke() inside event loop. "
                "Use await llm.ainvoke(...) instead."
            )
        except RuntimeError:
            return asyncio.run(self.ainvoke(prompt, config=config))


def get_llm():
    if not settings.ENABLE_LLM:
        raise RuntimeError("LLM disabled via config")

    return FallbackGeminiLLM()