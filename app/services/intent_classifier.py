# app/services/intent_classifier.py

"""
Intent Classification Service

Uses LLM to intelligently classify user intent and extract relevant information.
"""

import logging
import json
import re
from typing import Dict, Any, Optional
from enum import Enum

from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Possible user intents"""
    SYMPTOM_ANALYSIS = "symptom_analysis"
    INSURANCE_VERIFICATION = "insurance_verification"
    APPOINTMENT_BOOKING = "appointment_booking"
    HOSPITAL_NAVIGATION = "hospital_navigation"
    GENERAL_HEALTH_QUESTION = "general_health_question"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"


class IntentClassificationResult:
    """Container for intent classification results"""

    def __init__(
        self,
        intent: IntentType,
        confidence: float,
        extracted_entities: Dict[str, Any],
        reasoning: str,
        requires_more_info: bool = False,
        follow_up_questions: Optional[list] = None
    ):
        self.intent = intent
        self.confidence = confidence
        self.extracted_entities = extracted_entities
        self.reasoning = reasoning
        self.requires_more_info = requires_more_info
        self.follow_up_questions = follow_up_questions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "extracted_entities": self.extracted_entities,
            "reasoning": self.reasoning,
            "requires_more_info": self.requires_more_info,
            "follow_up_questions": self.follow_up_questions
        }


def classify_intent(user_input: str, conversation_history: Optional[list] = None) -> IntentClassificationResult:
    """
    Classify user intent using LLM.

    Args:
        user_input: The user's message/prompt
        conversation_history: Optional previous conversation for context

    Returns:
        IntentClassificationResult with classified intent and extracted entities
    """
    logger.info(f"Classifying intent for input: '{user_input[:100]}...'")

    llm = get_llm()

    # Build conversation context if available
    context_str = ""
    if conversation_history:
        context_str = "\n**Previous Conversation:**\n"
        for msg in conversation_history[-3:]:  # Last 3 messages for context
            context_str += f"- {msg.get('role', 'user')}: {msg.get('content', '')}\n"

    prompt = f"""
You are an intelligent healthcare assistant intent classifier. Your task is to analyze the user's input and determine their intent, then extract relevant information.

{context_str}

**Current User Input:**
"{user_input}"

**Available Intents:**

1. **symptom_analysis** - User is describing symptoms or health problems they're experiencing
   - Extract: symptoms (list), duration, severity, age, existing_conditions, medications, allergies
   - Examples: "I have a fever and cough", "My head hurts for 3 days", "chest pain and shortness of breath"

2. **insurance_verification** - User wants to verify insurance or discussing insurance details
   - Extract: provider_name, policy_number, policy_holder_name, dob, group_number
   - Examples: "Check my Blue Cross insurance", "verify policy ABC123", "my insurance is Aetna"

3. **appointment_booking** - User wants to book an appointment or find a doctor
   - Extract: 
     - specialty (if mentioned)
     - preferred_date
     - preferred_time
     - reason (reason for visit)
     - doctor_name
     - patient_name (full name of the patient)
     - patient_email (email address)
     - patient_phone (phone number)
     - appointment_type ("in-person" or "telemedicine")
   - Examples: 
     - "book appointment with cardiologist"
     - "schedule checkup next week"
     - "I want to book an appointment, my name is John Doe, email john@example.com, phone 555-1234"
     - "Book me a telemedicine appointment for next Monday"

4. **hospital_navigation** - User needs help navigating hospital, finding amenities, or asking about wait times
   - Extract: location_query, destination, amenity_type
   - Examples: "where is the cafeteria", "how to get to radiology", "where's the restroom", "what's my wait time"

5. **general_health_question** - General health questions, medical information, wellness advice
   - Extract: topic, question_type
   - Examples: "what is diabetes", "how to lower blood pressure", "explain this medical term"

6. **emergency** - Medical emergency requiring immediate attention
   - Extract: emergency_type, symptoms
   - Keywords: "emergency", "can't breathe", "severe pain", "unconscious", "bleeding heavily"

**Your Task:**
1. Analyze the user input AND conversation history for context
2. Determine the most likely intent
3. Extract all relevant entities/information mentioned (check both current input and conversation history)
4. Assess confidence (0.0 to 1.0)
5. Determine if more information is needed
6. Generate follow-up questions if needed

**IMPORTANT:**
- If symptoms include emergency keywords (chest pain, can't breathe, severe bleeding, loss of consciousness), classify as "emergency" with high confidence
- For **appointment_booking**, extract patient details from current input OR previous conversation history
- Extract as much information as possible from both user input and conversation context
- If critical information is missing, set requires_more_info=true and provide follow_up_questions
- For appointment_type, infer from context (e.g., "video call", "online", "virtual" → "telemedicine"; "visit", "in person" → "in-person")

**Respond ONLY with valid JSON in this exact format:**

For symptom_analysis:
{{
  "intent": "symptom_analysis",
  "confidence": 0.95,
  "reasoning": "User is describing specific symptoms (fever, cough) that need medical analysis",
  "extracted_entities": {{
    "symptoms": ["fever", "cough", "fatigue"],
    "duration": "3 days",
    "severity": 7,
    "age": null
  }},
  "requires_more_info": true,
  "follow_up_questions": [
    "How old are you?",
    "Do you have any existing medical conditions?"
  ]
}}

For appointment_booking:
{{
  "intent": "appointment_booking",
  "confidence": 0.9,
  "reasoning": "User wants to book an appointment and has provided contact details",
  "extracted_entities": {{
    "specialty": "cardiologist",
    "preferred_date": "2024-03-15",
    "preferred_time": "10:00 AM",
    "reason": "chest pain checkup",
    "doctor_name": null,
    "patient_name": "John Doe",
    "patient_email": "john@example.com",
    "patient_phone": "555-1234",
    "appointment_type": "in-person"
  }},
  "requires_more_info": false,
  "follow_up_questions": []
}}

**Valid intent values:** symptom_analysis, insurance_verification, appointment_booking, hospital_navigation, general_health_question, emergency, unknown
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Remove markdown code blocks if present
        content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE)

        result = json.loads(content)

        intent_value = result.get("intent", "unknown")
        try:
            intent = IntentType(intent_value)
        except ValueError:
            logger.warning(f"Unknown intent value: {intent_value}, defaulting to UNKNOWN")
            intent = IntentType.UNKNOWN

        confidence = result.get("confidence", 0.5)
        reasoning = result.get("reasoning", "")
        extracted_entities = result.get("extracted_entities", {})
        requires_more_info = result.get("requires_more_info", False)
        follow_up_questions = result.get("follow_up_questions", [])

        # Additional validation for appointment_booking
        if intent == IntentType.APPOINTMENT_BOOKING:
            required_fields = ["patient_name", "patient_email", "patient_phone", "reason"]
            missing_fields = [field for field in required_fields 
                            if not extracted_entities.get(field)]
            
            if missing_fields:
                requires_more_info = True
                # Generate follow-up questions for missing fields
                field_questions = {
                    "patient_name": "What is your full name?",
                    "patient_email": "What is your email address?",
                    "patient_phone": "What is your phone number?",
                    "reason": "What is the reason for your visit?"
                }
                follow_up_questions = [field_questions[field] for field in missing_fields 
                                      if field in field_questions]
                
                logger.info(f"Missing appointment booking fields: {missing_fields}")
            
            # Set default appointment_type if not specified
            if not extracted_entities.get("appointment_type"):
                extracted_entities["appointment_type"] = "in-person"

        logger.info(f"Intent classified: {intent.value} (confidence: {confidence})")
        logger.info(f"Reasoning: {reasoning}")
        if extracted_entities:
            logger.info(f"Extracted entities: {extracted_entities}")

        classification_result = IntentClassificationResult(
            intent=intent,
            confidence=confidence,
            extracted_entities=extracted_entities,
            reasoning=reasoning,
            requires_more_info=requires_more_info,
            follow_up_questions=follow_up_questions
        )

        return classification_result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {content}")

        # Fallback: try to detect intent with simple rules
        return _fallback_classification(user_input)

    except Exception as e:
        logger.error(f"Error during intent classification: {e}", exc_info=True)
        return _fallback_classification(user_input)
    


def _fallback_classification(user_input: str) -> IntentClassificationResult:
    """
    Rule-based fallback classification when LLM fails.

    Args:
        user_input: User's input text

    Returns:
        IntentClassificationResult with basic classification
    """
    logger.warning("Using fallback rule-based classification")

    input_lower = user_input.lower()

    # Emergency keywords
    emergency_keywords = [
        "emergency", "can't breathe", "cannot breathe", "chest pain",
        "severe pain", "unconscious", "bleeding heavily", "heart attack",
        "stroke", "choking", "severe bleeding"
    ]

    if any(keyword in input_lower for keyword in emergency_keywords):
        return IntentClassificationResult(
            intent=IntentType.EMERGENCY,
            confidence=0.9,
            extracted_entities={"symptoms": [user_input]},
            reasoning="Emergency keywords detected",
            requires_more_info=False
        )

    # Insurance keywords
    insurance_keywords = ["insurance", "policy", "coverage", "verify", "blue cross", "aetna", "cigna", "medicare"]
    if any(keyword in input_lower for keyword in insurance_keywords):
        return IntentClassificationResult(
            intent=IntentType.INSURANCE_VERIFICATION,
            confidence=0.7,
            extracted_entities={},
            reasoning="Insurance-related keywords detected",
            requires_more_info=True,
            follow_up_questions=["What is your insurance provider name?", "What is your policy number?"]
        )

    # Appointment booking keywords
    booking_keywords = ["book", "appointment", "schedule", "reserve", "see doctor"]
    if any(keyword in user_input for keyword in booking_keywords):
        return IntentClassificationResult(
            intent=IntentType.APPOINTMENT_BOOKING,
            confidence=0.6,
            extracted_entities={
                "appointment_type": "in-person"  # Default value
            },
            reasoning="Appointment booking keywords detected in fallback mode",
            requires_more_info=True,
            follow_up_questions=[
                "What is your full name?",
                "What is your email address?",
                "What is your phone number?",
                "What is the reason for your visit?"
            ]
        )

    # Navigation keywords
    navigation_keywords = ["where is", "how to get", "directions", "location", "cafeteria", "restroom", "pharmacy"]
    if any(keyword in input_lower for keyword in navigation_keywords):
        return IntentClassificationResult(
            intent=IntentType.HOSPITAL_NAVIGATION,
            confidence=0.7,
            extracted_entities={"location_query": user_input},
            reasoning="Navigation-related keywords detected",
            requires_more_info=False
        )

    # Symptom keywords (most common, check last)
    symptom_keywords = [
        "pain", "ache", "fever", "cough", "cold", "headache", "dizzy",
        "nausea", "vomit", "tired", "fatigue", "sick", "hurt", "sore"
    ]
    if any(keyword in input_lower for keyword in symptom_keywords):
        return IntentClassificationResult(
            intent=IntentType.SYMPTOM_ANALYSIS,
            confidence=0.6,
            extracted_entities={"symptoms": [user_input]},
            reasoning="Symptom-related keywords detected",
            requires_more_info=True,
            follow_up_questions=["How long have you had these symptoms?", "What is your age?"]
        )

    # Default to general health question
    return IntentClassificationResult(
        intent=IntentType.GENERAL_HEALTH_QUESTION,
        confidence=0.5,
        extracted_entities={"question": user_input},
        reasoning="No specific intent detected, assuming general question",
        requires_more_info=False
    )


def extract_symptoms_from_text(text: str) -> Dict[str, Any]:
    """
    Helper function to extract structured symptom information from text.

    Args:
        text: User's symptom description

    Returns:
        Dict with structured symptom data
    """
    llm = get_llm()

    prompt = f"""
Extract structured symptom information from the following text:

"{text}"

Respond ONLY with valid JSON:
{{
  "symptoms": ["symptom1", "symptom2"],
  "duration": "3 days" or null,
  "severity_1_10": 7 or null,
  "age": 35 or null,
  "existing_conditions": ["condition1"] or [],
  "medications": ["med1"] or [],
  "allergies": ["allergy1"] or []
}}
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE)
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error extracting symptoms: {e}")
        return {"symptoms": [text], "duration": None}
