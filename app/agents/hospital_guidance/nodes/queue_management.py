from typing import Dict, Any
import logging
from datetime import datetime, timedelta

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.tools.queue_tool import queue_tool
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

def update_wait_time(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Update patient's position in queue and wait time"""
    
    doctor_id = f"dr_{state['doctor_name'].lower().replace(' ', '_')}"
    queue_status = queue_tool.get_queue_status(state['patient_id'], doctor_id)
    
    if not queue_status:
        logger.warning(f"Patient {state['patient_id']} not found in queue")
        return state
    
    # Check if there's a significant change
    previous_wait = state.get("estimated_wait_time", 0)
    current_wait = queue_status["estimated_wait"]
    wait_change = abs(current_wait - previous_wait)
    
    # Notify if wait time changed significantly (>10 minutes)
    notification = None
    if wait_change > 10:
        if current_wait > previous_wait:
            notification = {
                "type": "warning",
                "title": "Wait Time Update",
                "message": f"Your appointment is running {current_wait - previous_wait} minutes behind schedule. New estimated wait: {current_wait} minutes.",
                "timestamp": datetime.now()
            }
        else:
            notification = {
                "type": "info",
                "title": "Good News!",
                "message": f"The doctor is running ahead of schedule. New estimated wait: {current_wait} minutes.",
                "timestamp": datetime.now()
            }
    
    # Check if patient is next
    if queue_tool.is_ready_for_patient(state['patient_id'], doctor_id):
        notification = {
            "type": "success",
            "title": "You're Next!",
            "message": f"Dr. {state['doctor_name']} will see you shortly. Please proceed to the exam room.",
            "timestamp": datetime.now(),
            "action": "proceed_to_exam"
        }
    
    return {
        **state,
        "queue_position": queue_status["queue_position"],
        "estimated_wait_time": queue_status["estimated_wait"],
        "last_wait_update": datetime.now(),
        "notifications": state.get("notifications", []) + ([notification] if notification else []),
        "last_updated": datetime.now()
    }


def suggest_activities_while_waiting(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Suggest activities based on wait time"""
    
    wait_time = state.get("estimated_wait_time", 0)
    
    if wait_time < 10:
        suggestions = [
            "Relax in the waiting room - you'll be called soon",
            "Complete any remaining pre-visit forms",
            "Review questions you want to ask the doctor"
        ]
    elif wait_time < 30:
        suggestions = [
            "Visit the restroom (2 minute walk)",
            "Grab a coffee from the cafeteria (5 minute walk)",
            "Complete pre-visit medical history forms",
            "Review your medication list"
        ]
    else:
        suggestions = [
            "Get a snack from the cafeteria (5 minute walk)",
            "Take a short walk around the hospital",
            "Complete any pending lab work to save time later",
            "Call your family to update them",
            "Read a magazine in the waiting area"
        ]
    
    # Use LLM to make suggestions conversational
    llm = get_llm()
    prompt = f"""
    The patient has a {wait_time} minute wait for their appointment.
    
    Suggest 2-3 activities they can do while waiting. Make it friendly and helpful.
    
    Options: {', '.join(suggestions)}
    
    Keep response brief (2-3 sentences).
    """
    
    try:
        response = llm.invoke(prompt)
        message = response.content
    except Exception as e:
        logger.error(f"Error generating suggestions: {e}")
        message = f"You have about {wait_time} minutes until your appointment. Here are some suggestions:\n" + "\n".join(f"• {s}" for s in suggestions[:3])
    
    return {
        **state,
        "notifications": state.get("notifications", []) + [{
            "type": "info",
            "title": "While You Wait",
            "message": message,
            "suggestions": suggestions,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def notify_family(state: HospitalGuidanceState, message: str) -> Dict[str, Any]:
    """Send notification to family members"""
    
    family_contacts = state.get("family_contacts", [])
    
    if not family_contacts:
        return state
    
    # In production, this would send actual SMS/email
    logger.info(f"Notifying {len(family_contacts)} family members: {message}")
    
    for contact in family_contacts:
        logger.info(f"Sent to {contact.get('name', 'Unknown')}: {message}")
    
    return {
        **state,
        "family_notified": True,
        "notifications": state.get("notifications", []) + [{
            "type": "info",
            "title": "Family Notified",
            "message": f"Your family has been updated: '{message}'",
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }