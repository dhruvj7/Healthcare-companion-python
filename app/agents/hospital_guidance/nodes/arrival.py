from typing import Dict, Any
import logging
from datetime import datetime

from app.agents.hospital_guidance.state import (
    HospitalGuidanceState, 
    JourneyStage,
    PriorityLevel
)
from app.agents.hospital_guidance.tools.navigation_tool import navigation_tool
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

def handle_arrival(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Handle patient arrival at hospital"""
    
    logger.info(f"Patient {state['patient_id']} arrived at hospital")
    
    # Set current location to entrance
    entrance = navigation_tool.find_location("main entrance")
    
    if not entrance:
        logger.error("Could not find main entrance location")
        entrance = {
            "building": "A",
            "floor": "1",
            "name": "Main Entrance",
            "coordinates": {"x": 0, "y": 0}
        }
    
    # Generate personalized greeting
    llm = get_llm()
    greeting_prompt = f"""
    Generate a warm, personalized greeting for a patient arriving at the hospital.
    
    Patient information:
    - Appointment with: {state['doctor_name']}
    - Appointment time: {state['appointment_time'].strftime('%I:%M %p')}
    - Reason: {state['reason_for_visit']}
    
    Keep it brief (2-3 sentences), welcoming, and mention their next step (check-in).
    """
    
    try:
        greeting_response = llm.invoke(greeting_prompt)
        greeting = greeting_response.content
    except Exception as e:
        logger.error(f"Error generating greeting: {e}")
        greeting = f"Welcome! You have an appointment with {state['doctor_name']} at {state['appointment_time'].strftime('%I:%M %p')}."
    
    # Create arrival notification
    notification = {
        "id": f"arrival_{datetime.now().timestamp()}",
        "type": "info",
        "priority": PriorityLevel.MEDIUM.value,
        "title": "Welcome to the Hospital",
        "message": greeting,
        "timestamp": datetime.now(),
        "action": "check_in"
    }
    
    # Find route to registration
    registration = navigation_tool.find_location("registration")
    route = None
    
    if registration:
        route = navigation_tool.calculate_route(entrance, registration)
    
    return {
        **state,
        "journey_stage": JourneyStage.ARRIVAL,
        "current_location": entrance,
        "destination": registration,
        "navigation_route": route["steps"] if route else None,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def initiate_check_in(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Start check-in process"""
    
    logger.info(f"Initiating check-in for patient {state['patient_id']}")
    
    # Simulate check-in steps
    check_in_tasks = []
    
    if not state.get("insurance_verified"):
        check_in_tasks.append({
            "task": "verify_insurance",
            "status": "pending",
            "description": "Verify insurance coverage",
            "required": True
        })
    
    if not state.get("forms_completed"):
        check_in_tasks.append({
            "task": "complete_forms",
            "status": "pending",
            "description": "Complete medical history forms",
            "required": True
        })
    
    if not state.get("copay_paid"):
        check_in_tasks.append({
            "task": "pay_copay",
            "status": "pending",
            "description": "Pay copayment ($45)",
            "required": True
        })
    
    notification = {
        "id": f"checkin_{datetime.now().timestamp()}",
        "type": "action_required",
        "priority": PriorityLevel.HIGH.value,
        "title": "Check-in Required",
        "message": f"Please complete {len(check_in_tasks)} check-in tasks",
        "timestamp": datetime.now(),
        "tasks": check_in_tasks
    }
    
    return {
        **state,
        "journey_stage": JourneyStage.CHECK_IN,
        "pending_tasks": check_in_tasks,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def complete_check_in(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Mark check-in as complete"""
    
    logger.info(f"Check-in completed for patient {state['patient_id']}")
    
    # Add to doctor's queue
    from app.agents.hospital_guidance.tools.queue_tool import queue_tool
    
    doctor_id = f"dr_{state['doctor_name'].lower().replace(' ', '_')}"
    queue_status = queue_tool.add_to_queue(
        state['patient_id'],
        doctor_id,
        state['appointment_time']
    )
    
    notification = {
        "id": f"checkin_complete_{datetime.now().timestamp()}",
        "type": "success",
        "priority": PriorityLevel.MEDIUM.value,
        "title": "Check-in Complete!",
        "message": f"You're #{queue_status['queue_position']} in line. Estimated wait: {queue_status['estimated_wait']} minutes.",
        "timestamp": datetime.now()
    }
    
    # Navigate to waiting room
    waiting_room = navigation_tool.find_location("waiting room")
    route = None
    
    if waiting_room and state.get("current_location"):
        route = navigation_tool.calculate_route(
            state["current_location"],
            waiting_room
        )
    
    return {
        **state,
        "journey_stage": JourneyStage.PRE_VISIT,
        "check_in_completed": True,
        "insurance_verified": True,
        "forms_completed": True,
        "copay_paid": True,
        "queue_position": queue_status["queue_position"],
        "estimated_wait_time": queue_status["estimated_wait"],
        "destination": waiting_room,
        "navigation_route": route["steps"] if route else None,
        "notifications": state.get("notifications", []) + [notification],
        "completed_tasks": ["verify_insurance", "complete_forms", "pay_copay"],
        "pending_tasks": [],
        "last_updated": datetime.now()
    }