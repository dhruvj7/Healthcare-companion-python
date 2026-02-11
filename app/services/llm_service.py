from langchain_core.runnables import Runnable
from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted
from app.core.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)


class FallbackGeminiLLM(Runnable):
    """
    Gemini LLM wrapper with:
    - Model fallback
    - Async-safe execution
    - LangGraph compatible
    """

    def __init__(self):
        self.models = [
            settings.PRIMARY_LLM_MODEL,
            *settings.FALLBACK_LLM_MODELS
        ]

    async def _async_invoke(self, llm, prompt: str):
        """Async wrapper for LLM invocation"""
        try:
            # Use ainvoke for async operation
            response = await llm.ainvoke(prompt)
            return response
        except Exception as e:
            raise e
    
    async def ainvoke(self, prompt: str, timeout: int = 10):
        """Async invoke with fallback"""
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
                
                response = await asyncio.wait_for(
                    self._async_invoke(llm, prompt),
                    timeout=timeout,
                )
                
                logger.info(f"Gemini success with model: {model_name}")
                return response
                
            except asyncio.TimeoutError:
                logger.warning(f"Gemini model timed out [{model_name}]")
                last_error = TimeoutError(f"Model {model_name} timed out")
                continue
                
            except Exception as e:
                logger.warning(f"Gemini model failed [{model_name}]: {e}")
                last_error = e
                continue
        
        logger.error("All Gemini models exhausted")
        raise last_error or RuntimeError("All LLM models failed")
    
    def invoke(self, prompt: str, timeout: int = 10):
        last_error = None

        for model_name in self.models:
            try:
                logger.info(f"Trying Gemini model: {model_name}")

                llm = ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=settings.LLM_TEMPERATURE,
                    google_api_key=settings.GOOGLE_API_KEY,
                    max_output_tokens=settings.LLM_MAX_TOKENS
                )

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
                logger.warning(f"Quota exhausted for model [{model_name}]")
                last_error = e
                continue

            except Exception as e:
                logger.warning(f"Gemini model failed [{model_name}]: {e}")
                last_error = e
                continue

        logger.error("All Gemini models exhausted")
        raise last_error or RuntimeError("All LLM models failed")

    # --------------------------------------------------
    # 🔥 SYNC (Required by Runnable interface)
    # --------------------------------------------------
    def invoke(self, prompt, config=None):
        """
        Safe sync wrapper.
        DO NOT use asyncio.run() inside event loop.
        """
        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot use sync invoke() inside running event loop. "
                "Use await llm.ainvoke(...) instead."
            )
        except RuntimeError:
            return asyncio.run(self.ainvoke(prompt, config=config))


def get_llm():
    if not settings.ENABLE_LLM:
        raise RuntimeError("LLM disabled via config")

    return FallbackGeminiLLM()
