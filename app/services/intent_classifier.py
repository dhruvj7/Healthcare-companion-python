# app/services/intent_classifier.py

"""
Multi-Intent Classification Service (Production Ready)

Supports:
- Multiple intents per message
- Execution ordering
- Emergency override
- Robust JSON parsing
- Fallback classification
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List
from enum import Enum

from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    SYMPTOM_ANALYSIS = "symptom_analysis"
    INSURANCE_VERIFICATION = "insurance_verification"
    APPOINTMENT_BOOKING = "appointment_booking"
    HOSPITAL_NAVIGATION = "hospital_navigation"
    GENERAL_HEALTH_QUESTION = "general_health_question"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


class MultiIntentClassificationResult:
    def __init__(
        self,
        intents: List[IntentType],
        execution_order: List[IntentType],
        confidence: float,
        reasoning: str,
        extracted_entities: Dict[str, Any],
        requires_sequential_execution: bool,
    ):
        self.intents = intents
        self.execution_order = execution_order
        self.confidence = confidence
        self.reasoning = reasoning
        self.extracted_entities = extracted_entities
        self.requires_sequential_execution = requires_sequential_execution

    def to_dict(self):
        return {
            "intents": [i.value for i in self.intents],
            "execution_order": [i.value for i in self.execution_order],
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "extracted_entities": self.extracted_entities,
            "requires_sequential_execution": self.requires_sequential_execution,
        }


# ---------------------------------------------------------
# MAIN MULTI INTENT CLASSIFIER
# ---------------------------------------------------------

async def classify_intents(
    user_input: str,
    conversation_history: Optional[list] = None
) -> MultiIntentClassificationResult:

    llm = get_llm()

    context_str = ""
    if conversation_history:
        context_str = "\nPrevious conversation:\n"
        for msg in conversation_history[-3:]:
            context_str += f"- {msg.get('role')}: {msg.get('content')}\n"

    prompt = f"""
You are a healthcare AI orchestration planner.

Analyze the user input and detect ALL relevant intents.
Determine correct execution order.

User Input:
"{user_input}"

Available intents:
- symptom_analysis
- insurance_verification
- appointment_booking
- hospital_navigation
- general_health_question
- emergency

IMPORTANT:
- If emergency symptoms exist → emergency MUST be first and ONLY intent.
- If symptom_analysis + appointment_booking → symptom_analysis must run first.
- Respond ONLY in valid JSON.

Format:
{{
  "intents": ["symptom_analysis", "appointment_booking"],
  "execution_order": ["symptom_analysis", "appointment_booking"],
  "confidence": 0.95,
  "reasoning": "User wants symptom analysis followed by booking",
  "extracted_entities": {{}},
  "requires_sequential_execution": true
}}
"""

    try:
        response = await llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE)
        data = json.loads(content)

        intents = [
            IntentType(i) if i in IntentType._value2member_map_ else IntentType.UNKNOWN
            for i in data.get("intents", [])
        ]

        execution_order = [
            IntentType(i) if i in IntentType._value2member_map_ else IntentType.UNKNOWN
            for i in data.get("execution_order", [])
        ]

        return MultiIntentClassificationResult(
            intents=intents or [IntentType.UNKNOWN],
            execution_order=execution_order or intents,
            confidence=data.get("confidence", 0.7),
            reasoning=data.get("reasoning", ""),
            extracted_entities=data.get("extracted_entities", {}),
            requires_sequential_execution=data.get("requires_sequential_execution", True),
        )

    except Exception as e:
        logger.error("Multi-intent classification failed", exc_info=True)
        return _fallback_classification(user_input)


# ---------------------------------------------------------
# FALLBACK CLASSIFIER (SAFE RULE-BASED)
# ---------------------------------------------------------

def _fallback_classification(user_input: str) -> MultiIntentClassificationResult:

    input_lower = user_input.lower()

    emergency_keywords = [
        "chest pain", "can't breathe", "unconscious",
        "bleeding heavily", "heart attack", "stroke"
    ]

    if any(k in input_lower for k in emergency_keywords):
        return MultiIntentClassificationResult(
            intents=[IntentType.EMERGENCY],
            execution_order=[IntentType.EMERGENCY],
            confidence=0.9,
            reasoning="Emergency keywords detected",
            extracted_entities={"symptoms": [user_input]},
            requires_sequential_execution=True,
        )

    intents = []

    if any(k in input_lower for k in ["pain", "fever", "cough", "headache"]):
        intents.append(IntentType.SYMPTOM_ANALYSIS)

    if any(k in input_lower for k in ["book", "appointment", "schedule"]):
        intents.append(IntentType.APPOINTMENT_BOOKING)

    if not intents:
        intents = [IntentType.GENERAL_HEALTH_QUESTION]

    return MultiIntentClassificationResult(
        intents=intents,
        execution_order=intents,
        confidence=0.6,
        reasoning="Fallback classification",
        extracted_entities={},
        requires_sequential_execution=True,
    )
