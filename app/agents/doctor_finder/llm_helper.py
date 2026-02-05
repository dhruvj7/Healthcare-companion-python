import json
import logging
import re
from typing import Optional

from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a clinical decision-support system.
You do NOT diagnose patients.
You ONLY map symptoms or suspected conditions to ONE medical specialty.

Rules:
- Choose ONE primary specialty
- Be conservative
- Prefer General Medicine if unsure
- Output STRICT JSON only
"""

def llm_resolve_specialty(text: str) -> Optional[str]:
    """
    Uses LLM to infer a medical specialty from symptom or diagnosis text.
    Returns specialty string or None.
    """

    llm = get_llm()

    prompt = f"""
{SYSTEM_PROMPT}

Patient description:
\"\"\"{text}\"\"\"

Respond ONLY with valid JSON:
{{
  "recommended_specialty": "Cardiology",
  "confidence": 0.0
}}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        content = re.sub(r'^```json\s*|\s*```$', '', content)

        data = json.loads(content)

        if data.get("confidence", 0) >= 0.7:
            return data.get("recommended_specialty")

    except Exception as e:
        logger.warning(f"LLM specialty resolution failed: {e}", exc_info=True)

    return None
