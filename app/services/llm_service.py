from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted
from app.core.config import settings
import logging
import asyncio

logger = logging.getLogger(__name__)


class FallbackGeminiLLM:
    """
    Gemini LLM wrapper with:
    - Model fallback
    - Fast quota detection
    - Timeout control
    """

    def __init__(self):
        self.models = [
            settings.PRIMARY_LLM_MODEL,
            *settings.FALLBACK_LLM_MODELS
        ]

    def invoke(self, prompt: str, timeout: int = 8):
        last_error = None

        for model_name in self.models:
            try:
                logger.info(f"Trying Gemini model: {model_name}")

                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=settings.LLM_TEMPERATURE,
                    google_api_key=settings.GOOGLE_API_KEY,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                    timeout=timeout,  # critical
                )

                # Hard timeout wrapper
                response = asyncio.run(
                    asyncio.wait_for(
                        self._async_invoke(llm, prompt),
                        timeout=timeout,
                    )
                )

                if response and response.content:
                    logger.info(f"Gemini success with model: {model_name}")
                    return response

            except ResourceExhausted as e:
                logger.warning(
                    f"Quota exhausted for model [{model_name}]"
                )
                last_error = e
                continue

            except asyncio.TimeoutError:
                logger.warning(
                    f"Timeout for model [{model_name}]"
                )
                last_error = TimeoutError("LLM timeout")
                continue

            except Exception as e:
                logger.warning(
                    f"Gemini model failed [{model_name}]: {e}"
                )
                last_error = e
                continue

        logger.error("All Gemini models exhausted")
        raise last_error or RuntimeError("All LLM models failed")

    async def _async_invoke(self, llm, prompt):
        return await llm.ainvoke(prompt)



def get_llm():
    """
    Returns a Gemini LLM with automatic fallback.
    Call site remains unchanged.
    """
    if not settings.ENABLE_LLM:
        raise RuntimeError("LLM disabled via config")

    return FallbackGeminiLLM()
