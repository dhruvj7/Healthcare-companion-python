from typing import Dict, Any, List
import logging
from datetime import datetime

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage, PriorityLevel
from app.agents.hospital_guidance.tools.navigation_tool import navigation_tool
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

# Emergency keywords and symptoms
EMERGENCY_SYMPTOMS = {
    "cardiac": [
        "severe chest pain", "crushing chest pain", "chest pressure",
        "pain radiating to arm", "pain radiating to jaw"
    ],
    "neurological": [
        "sudden severe headache", "worst headache", "confusion",
        "slurred speech", "facial drooping", "weakness one side",
        "loss of consciousness", "seizure", "can't move arm", "can't move leg"
    ],
    "respiratory": [
        "severe difficulty breathing", "can't breathe", "gasping",
        "blue lips", "choking", "can't speak"
    ],
    "bleeding": [
        "uncontrolled bleeding", "severe bleeding", "blood loss",
        "coughing blood", "vomiting blood"
    ],
    "allergic": [
        "severe allergic reaction", "throat swelling", "tongue swelling",
        "anaphylaxis", "hives with breathing difficulty"
    ],
    "mental_health": [
        "suicidal thoughts", "want to hurt myself", "want to hurt others",
        "self harm"
    ],
    "trauma": [
        "severe injury", "broken bone visible", "deep wound",
        "severe burn", "head trauma"
    ]
}

def detect_emergency(state: HospitalGuidanceState, user_message: str) -> Dict[str, Any]:
    """Detect if user message indicates emergency"""
    
    message_lower = user_message.lower()
    emergency_detected = False
    emergency_type = None
    
    # Check for emergency keywords
    for category, symptoms in EMERGENCY_SYMPTOMS.items():
        for symptom in symptoms:
            if symptom in message_lower:
                emergency_detected = True
                emergency_type = category
                logger.critical(f"EMERGENCY DETECTED: {category} - '{symptom}' in message")
                break
        if emergency_detected:
            break
    
    # Also check for explicit emergency words
    emergency_words = ["emergency", "help", "urgent", "911", "ambulance", "dying"]
    if any(word in message_lower for word in emergency_words):
        emergency_detected = True
        if not emergency_type:
            emergency_type = "general"
    
    if emergency_detected:
        return handle_emergency(state, emergency_type, user_message)
    
    return state


def handle_emergency(
    state: HospitalGuidanceState,
    emergency_type: str,
    user_message: str
) -> Dict[str, Any]:
    """Handle emergency situation"""
    
    logger.critical(f"EMERGENCY ACTIVATED for patient {state['patient_id']}: {emergency_type}")
    
    # Immediate emergency response
    emergency_response = {
        "cardiac": "🚨 CARDIAC EMERGENCY - Alerting medical staff immediately. Stay where you are. Do not move.",
        "neurological": "🚨 NEUROLOGICAL EMERGENCY - Medical team has been alerted. Sit down if possible. Help is on the way.",
        "respiratory": "🚨 BREATHING EMERGENCY - Emergency team alerted. Try to stay calm. Help arriving immediately.",
        "bleeding": "🚨 BLEEDING EMERGENCY - Medical staff alerted. Apply pressure if possible. Do not move.",
        "allergic": "🚨 ALLERGIC REACTION - Emergency team notified. Lie down if possible. Help is coming.",
        "mental_health": "🚨 MENTAL HEALTH CRISIS - Crisis team alerted. You're not alone. Someone will be with you immediately.",
        "trauma": "🚨 TRAUMA EMERGENCY - Medical team alerted. Do not move injured area. Help is on the way.",
        "general": "🚨 EMERGENCY - Hospital staff have been alerted to your location. Stay where you are. Help is coming immediately."
    }
    
    response_message = emergency_response.get(emergency_type, emergency_response["general"])
    
    # Get current location or last known location
    current_location = state.get("current_location")
    if not current_location:
        current_location = {"name": "Unknown location", "building": "Unknown", "floor": "Unknown"}
    
    # Create emergency alert
    emergency_alert = {
        "id": f"emergency_{datetime.now().timestamp()}",
        "type": "emergency",
        "priority": PriorityLevel.CRITICAL.value,
        "title": "🚨 EMERGENCY",
        "message": response_message,
        "emergency_type": emergency_type,
        "patient_id": state['patient_id'],
        "location": current_location,
        "user_message": user_message,
        "timestamp": datetime.now(),
        "status": "active"
    }
    
    # Alert family immediately
    family_message = f"EMERGENCY: {state.get('patient_id', 'Patient')} has requested emergency assistance at {current_location.get('name', 'hospital')}. Hospital staff have been notified."
    
    # In production, this would:
    # 1. Send alert to hospital emergency system
    # 2. Notify nearest medical staff
    # 3. Alert family via SMS/call
    # 4. Activate emergency protocols
    
    logger.critical(f"Emergency alert sent: {emergency_alert}")
    logger.critical(f"Family notification: {family_message}")
    
    # Provide immediate instructions based on emergency type
    immediate_instructions = _get_emergency_instructions(emergency_type)
    
    return {
        **state,
        "emergency_active": True,
        "emergency_type": emergency_type,
        "emergency_location": current_location,
        "journey_stage": JourneyStage.IN_VISIT,  # Override current stage
        "alerts": state.get("alerts", []) + [emergency_alert],
        "notifications": state.get("notifications", []) + [
            {
                "type": "emergency",
                "title": "Emergency Services Activated",
                "message": response_message,
                "instructions": immediate_instructions,
                "timestamp": datetime.now()
            }
        ],
        "family_notified": True,
        "last_updated": datetime.now()
    }


def _get_emergency_instructions(emergency_type: str) -> List[str]:
    """Get immediate instructions for different emergency types"""
    
    instructions = {
        "cardiac": [
            "Stay as still as possible",
            "If you have aspirin, chew one tablet (if not allergic)",
            "Loosen tight clothing",
            "Medical team arriving in less than 2 minutes"
        ],
        "neurological": [
            "Sit or lie down immediately",
            "Do not try to walk",
            "Note what time symptoms started",
            "Medical team arriving immediately"
        ],
        "respiratory": [
            "Try to stay calm - panic makes breathing harder",
            "Sit upright if possible",
            "Loosen tight clothing around neck and chest",
            "Emergency team arriving now"
        ],
        "bleeding": [
            "Apply firm pressure to the wound if possible",
            "Do not remove any objects from wounds",
            "Stay still to reduce blood flow",
            "Medical team arriving immediately"
        ],
        "allergic": [
            "Use EpiPen if you have one",
            "Lie flat with legs elevated (unless breathing difficulty)",
            "Remove any allergen if possible",
            "Emergency response team notified"
        ],
        "mental_health": [
            "You're safe here",
            "Crisis counselor will be with you in moments",
            "Focus on your breathing if you can",
            "You are not alone"
        ],
        "general": [
            "Stay where you are",
            "Medical staff have been alerted",
            "Help is on the way",
            "Try to stay calm"
        ]
    }
    
    return instructions.get(emergency_type, instructions["general"])


def resolve_emergency(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Mark emergency as resolved"""
    
    logger.info(f"Emergency resolved for patient {state['patient_id']}")
    
    # Update emergency status
    alerts = state.get("alerts", [])
    for alert in alerts:
        if alert.get("type") == "emergency" and alert.get("status") == "active":
            alert["status"] = "resolved"
            alert["resolved_at"] = datetime.now()
    
    notification = {
        "type": "success",
        "title": "Emergency Resolved",
        "message": "You're being taken care of. Medical team is with you.",
        "timestamp": datetime.now()
    }
    
    return {
        **state,
        "emergency_active": False,
        "alerts": alerts,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def provide_emotional_support(state: HospitalGuidanceState, concern: str) -> Dict[str, Any]:
    """Provide emotional support and reassurance"""
    
    logger.info(f"Providing emotional support for: {concern}")
    
    llm = get_llm()
    support_prompt = f"""
    Provide empathetic, supportive response to a patient expressing concern or anxiety.
    
    Patient concern: {concern}
    Context: Patient is in hospital for {state.get('reason_for_visit', 'medical visit')}
    
    Guidelines:
    - Be warm, empathetic, and reassuring
    - Acknowledge their feelings
    - Provide practical comfort
    - Offer helpful options (breathing exercise, speak with staff, etc.)
    - Keep it brief (3-4 sentences)
    
    DO NOT provide medical advice.
    """
    
    try:
        support_response = llm.invoke(support_prompt)
        support_message = support_response.content
    except Exception as e:
        logger.error(f"Error generating support message: {e}")
        support_message = "I understand this can be stressful. You're in good hands here. Would you like me to connect you with a staff member?"
    
    # Offer coping resources
    resources = [
        {
            "type": "breathing_exercise",
            "title": "Guided Breathing (2 minutes)",
            "description": "Calm anxiety with breathing"
        },
        {
            "type": "speak_to_staff",
            "title": "Speak with Staff Member",
            "description": "Connect with patient advocate"
        },
        {
            "type": "call_family",
            "title": "Call Family/Friend",
            "description": "Connect with your support person"
        }
    ]
    
    return {
        **state,
        "notifications": state.get("notifications", []) + [{
            "type": "support",
            "title": "We're Here to Help",
            "message": support_message,
            "resources": resources,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }