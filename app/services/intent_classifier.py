# app/services/intent_classifier.py

"""
Multi-Intent Classification Service (Production Ready)
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
    DOCTOR_SUGGESTION = "doctor_suggestion"
    UNKNOWN = "unknown"


class MultiIntentClassificationResult:
    def __init__(
        self,
        intents: List[IntentType],
        execution_order: List[IntentType],
        confidence: float,
        reasoning: str,
        extracted_entities: Dict[str, Any],
        requires_sequential_execution: bool = True,
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
    conversation_history: Optional[list] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> MultiIntentClassificationResult:
    logger.info("Starting process to classify intent...")
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

{context_str}

Additional Context (convert ALL relevant fields into extracted_entities: Dict[str, Any]):
{additional_context}

There are following possible intents:
- symptom_analysis
- insurance_verification
- appointment_booking
- hospital_navigation
- general_health_question
- emergency
- doctor_suggestion (user wants a list of doctors by specialty, e.g. "suggest 5 cardiologists", "find me cardiologist doctors", "list dermatologists")

For doctor_suggestion, extract: specialty (e.g. cardiologist, cardiology, dermatology), and optionally limit/count (e.g. 5, 10).
If user says "suggest any 5 doctors cardiologist" -> intents: ["doctor_suggestion"], extracted_entities: {{"specialty": "Cardiology", "limit": 5}}

Respond ONLY with valid JSON in this format:
{{
  "intents": ["symptom_analysis"],
  "execution_order": ["symptom_analysis"],
  "confidence": 0.9,
  "reasoning": "reason",
  "extracted_entities": {{}},
  "requires_sequential_execution": true
}}

Rules:
1. extracted_entities must be output in Python typing format: Dict[str, Any]
2. Convert all relevant fields from additional_context into extracted_entities.
3. Only omit a field if it is clearly irrelevant to the detected intents.
4. If no relevant entities exist, return an empty Dict[str, Any] as {{}}.
5. The output must be valid JSON only (no markdown, no extra text).
"""

    try:
        response = await llm.ainvoke(prompt)
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

    except Exception:
        logger.error("Multi-intent classification failed", exc_info=True)
        return _fallback_classification(user_input)


# ---------------------------------------------------------
# FALLBACK CLASSIFIER (SAFE RULE-BASED)
# ---------------------------------------------------------

# def _fallback_classification(user_input: str) -> MultiIntentClassificationResult:

#     input_lower = user_input.lower()

#     emergency_keywords = [
#         "chest pain", "can't breathe", "unconscious",
#         "bleeding heavily", "heart attack", "stroke"
#     ]

#     if any(k in input_lower for k in emergency_keywords):
#         return MultiIntentClassificationResult(
#             intents=[IntentType.EMERGENCY],
#             execution_order=[IntentType.EMERGENCY],
#             confidence=0.9,
#             reasoning="Emergency keywords detected",
#             extracted_entities={"symptoms": [user_input]},
#             requires_sequential_execution=True,
#         )

#     intents = []

#     if any(k in input_lower for k in ["pain", "fever", "cough", "headache"]):
#         intents.append(IntentType.SYMPTOM_ANALYSIS)

#     if any(k in input_lower for k in ["book", "appointment", "schedule"]):
#         intents.append(IntentType.APPOINTMENT_BOOKING)

#     if not intents:
#         intents = [IntentType.GENERAL_HEALTH_QUESTION]

#     return MultiIntentClassificationResult(
#         intents=intents,
#         execution_order=intents,
#         confidence=0.6,
#         reasoning="Fallback classification",
#         extracted_entities={},
#         requires_sequential_execution=True,
#     )
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
            extracted_entities={},
            requires_sequential_execution=False,
        )

    intents = []

    # -----------------------------------
    # 🏥 Hospital Navigation Detection
    # -----------------------------------
    navigation_keywords = [
        "navigate", "directions", "where is", "how do i get to",
        "route to", "find the", "locate", "cafeteria",
        "pharmacy", "icu", "ward", "reception", "billing",
        "lab", "laboratory", "radiology", "emergency room"
    ]

    if any(k in input_lower for k in navigation_keywords):
        intents.append(IntentType.HOSPITAL_NAVIGATION)
    logger.info("the intent inside the fall back is ", intents)  
    # -----------------------------------
    # 🤒 Symptom Analysis
    # -----------------------------------
    if any(k in input_lower for k in ["pain", "fever", "cough", "headache"]):
        intents.append(IntentType.SYMPTOM_ANALYSIS)

    # -----------------------------------
    # 📅 Appointment Booking
    # -----------------------------------
    if any(k in input_lower for k in ["book", "appointment", "schedule"]):
        intents.append(IntentType.APPOINTMENT_BOOKING)

    if any(k in input_lower for k in ["insurance", "policy", "coverage"]):
        intents.append(IntentType.INSURANCE_VERIFICATION)

    if any(k in input_lower for k in ["where is", "directions", "location"]):
        intents.append(IntentType.HOSPITAL_NAVIGATION)

    # -----------------------------------
    # 👨‍⚕️ Doctor suggestion (suggest doctors by specialty)
    # -----------------------------------
    doctor_keywords = [
        "suggest", "recommend", "find", "list", "show", "give me",
        "doctors", "cardiologist", "dermatologist", "pediatrician",
        "neurologist", "orthopedic", "psychiatrist", "ophthalmologist",
        "general practitioner", "physician"
    ]
    if any(k in input_lower for k in doctor_keywords) and any(
        s in input_lower for s in ["doctor", "cardiologist", "dermatologist", "pediatrician", "neurologist", "orthopedic", "psychiatrist", "ophthalmologist", "physician", "specialist"]
    ):
        intents.append(IntentType.DOCTOR_SUGGESTION)

    if not intents:
        intents = [IntentType.GENERAL_HEALTH_QUESTION]

    return MultiIntentClassificationResult(
        intents=intents,
        execution_order=intents,
        confidence=0.7,
        reasoning="Fallback rule-based classification",
        extracted_entities={},
        requires_sequential_execution=True,
    )  