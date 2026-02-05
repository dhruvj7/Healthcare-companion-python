from typing import Dict, Any
import logging
from datetime import datetime, timedelta

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.events import EventType, LocationArea

logger = logging.getLogger(__name__)

def route_event(state: HospitalGuidanceState) -> Dict[str, Any]:
    """
    Analyze event and determine what actions agent should take
    This is the BRAIN of the autonomous system
    """
    
    event = state.get("current_event")
    if not event:
        logger.warning("No event to route")
        return state
    
    event_type = event.get("type")
    event_data = event.get("data", {})
    current_stage = state.get("journey_stage")
    
    logger.info(f"Routing event: {event_type} | Current stage: {current_stage}")
    
    # Determine what needs to be done
    actions_needed = []
    
    # ===== EMERGENCY EVENTS (HIGHEST PRIORITY) =====
    if event_type == EventType.EMERGENCY_DETECTED.value:
        actions_needed = ["handle_emergency"]
    
    # ===== LOCATION EVENTS =====
    elif event_type == EventType.LOCATION_UPDATED.value:
        actions_needed = handle_location_update(state, event_data)
    
    elif event_type == EventType.ENTERED_HOSPITAL.value:
        actions_needed = handle_hospital_entry(state)
    
    elif event_type == EventType.REACHED_REGISTRATION.value:
        actions_needed = handle_reached_registration(state)
    
    elif event_type == EventType.REACHED_WAITING_ROOM.value:
        actions_needed = handle_reached_waiting_room(state)
    
    elif event_type == EventType.REACHED_EXAM_ROOM.value:
        actions_needed = handle_reached_exam_room(state)
    
    # ===== QUEUE EVENTS =====
    elif event_type == EventType.QUEUE_POSITION_CHANGED.value:
        actions_needed = handle_queue_change(state, event_data)
    
    elif event_type == EventType.NEXT_IN_QUEUE.value:
        actions_needed = ["notify_next_in_queue", "provide_navigation_to_exam"]
    
    # ===== TIME EVENTS =====
    elif event_type == EventType.APPOINTMENT_TIME_NEAR.value:
        actions_needed = handle_appointment_near(state)
    
    # ===== USER INTERACTION EVENTS =====
    elif event_type == EventType.USER_MESSAGE.value:
        actions_needed = ["detect_intent", "handle_user_query"]
    
    # ===== SYSTEM EVENTS =====
    elif event_type == EventType.VISIT_ENDED.value:
        actions_needed = ["create_post_visit_tasks", "generate_discharge"]
    
    else:
        logger.info(f"No specific handler for event type: {event_type}")
        actions_needed = []
    
    # Store determined actions
    state["steps_pending"] = actions_needed
    
    # Add to event history
    event_history = state.get("event_history", [])
    event_history.append({
        **event,
        "processed_at": datetime.now(),
        "actions_triggered": actions_needed
    })
    state["event_history"] = event_history
    
    return state


def handle_location_update(state: HospitalGuidanceState, event_data: Dict) -> list:
    """Determine actions based on location update"""
    
    detected_area = event_data.get("detected_area")
    current_stage = state.get("journey_stage")
    
    logger.info(f"Location update: area={detected_area}, stage={current_stage}")
    
    # Update detected area in state
    state["detected_area"] = detected_area
    state["last_location_update"] = datetime.now()
    
    # Determine what should happen based on area
    area_stage_map = {
        LocationArea.ENTRANCE.value: JourneyStage.ARRIVAL,
        LocationArea.REGISTRATION.value: JourneyStage.CHECK_IN,
        LocationArea.WAITING_ROOM.value: JourneyStage.WAITING,
        LocationArea.EXAM_ROOM.value: JourneyStage.IN_VISIT,
        LocationArea.PHARMACY.value: JourneyStage.POST_VISIT,
        LocationArea.EXIT.value: JourneyStage.DEPARTURE
    }
    
    expected_stage = area_stage_map.get(detected_area)
    
    if not expected_stage:
        return []  # Unknown area, no action
    
    # If patient is ahead of where they should be, catch them up
    if expected_stage and current_stage != expected_stage:
        return determine_catchup_actions(current_stage, expected_stage, state)
    
    return []


def handle_hospital_entry(state: HospitalGuidanceState) -> list:
    """Patient entered hospital"""
    
    # If no session yet, initialize
    if not state.get("session_id"):
        return ["initialize_session", "handle_arrival", "navigate_to_registration"]
    
    # If session exists but not arrived
    if state.get("journey_stage") != JourneyStage.ARRIVAL:
        return ["handle_arrival", "navigate_to_registration"]
    
    return []


def handle_reached_registration(state: HospitalGuidanceState) -> list:
    """Patient reached registration area"""
    
    current_stage = state.get("journey_stage")
    
    # If haven't checked in yet, start check-in flow
    if not state.get("check_in_completed"):
        return ["initiate_check_in", "complete_check_in", "update_location"]
    
    # If already checked in but still at registration, guide to waiting room
    if current_stage in [JourneyStage.ARRIVAL, JourneyStage.CHECK_IN]:
        return ["navigate_to_waiting_room"]
    
    return []


def handle_reached_waiting_room(state: HospitalGuidanceState) -> list:
    """Patient reached waiting room"""
    
    actions = ["update_location"]
    
    # Make sure they're in queue
    if not state.get("queue_position"):
        actions.append("add_to_queue")
    
    # Update wait time
    actions.append("update_wait_time")
    
    # Suggest activities
    actions.append("suggest_activities")
    
    return actions


def handle_reached_exam_room(state: HospitalGuidanceState) -> list:
    """Patient reached exam room"""
    
    # Start visit if not already started
    if not state.get("visit_started"):
        return ["update_location", "start_visit", "generate_questions"]
    
    return ["update_location"]


def handle_queue_change(state: HospitalGuidanceState, event_data: Dict) -> list:
    """Queue position changed"""
    
    new_position = event_data.get("new_position")
    
    actions = ["update_wait_time"]
    
    # If next in queue, notify
    if new_position == 1:
        actions.append("notify_next_in_queue")
    
    # If wait time significantly changed, suggest activities
    if state.get("estimated_wait_time", 0) > 20:
        actions.append("suggest_activities")
    
    return actions


def handle_appointment_near(state: HospitalGuidanceState) -> list:
    """Appointment time is approaching"""
    
    appointment_time = state.get("appointment_time")
    current_stage = state.get("journey_stage")
    
    actions = []
    
    # If patient not at hospital yet
    if current_stage not in [JourneyStage.ARRIVAL, JourneyStage.CHECK_IN, 
                             JourneyStage.WAITING, JourneyStage.IN_VISIT]:
        actions.append("send_reminder_notification")
    
    # If at hospital but not checked in
    if current_stage == JourneyStage.ARRIVAL and not state.get("check_in_completed"):
        actions.append("remind_check_in")
    
    return actions


def determine_catchup_actions(
    current_stage: JourneyStage, 
    target_stage: JourneyStage,
    state: HospitalGuidanceState
) -> list:
    """
    Determine what actions needed to catch patient up from current to target stage
    This enables multi-step autonomous progression
    """
    
    # Define journey progression
    progression = [
        JourneyStage.ARRIVAL,
        JourneyStage.CHECK_IN,
        JourneyStage.PRE_VISIT,
        JourneyStage.WAITING,
        JourneyStage.IN_VISIT,
        JourneyStage.POST_VISIT,
        JourneyStage.DEPARTURE,
        JourneyStage.COMPLETED
    ]
    
    # Find indices
    try:
        current_idx = progression.index(current_stage) if current_stage else -1
    except ValueError:
        current_idx = -1
    
    try:
        target_idx = progression.index(target_stage)
    except ValueError:
        return []
    
    # Build action list
    actions = []
    
    for i in range(current_idx + 1, target_idx + 1):
        stage = progression[i]
        
        if stage == JourneyStage.ARRIVAL:
            actions.extend(["handle_arrival"])
        
        elif stage == JourneyStage.CHECK_IN:
            if not state.get("check_in_completed"):
                actions.extend(["initiate_check_in", "complete_check_in"])
        
        elif stage == JourneyStage.PRE_VISIT or stage == JourneyStage.WAITING:
            actions.extend(["update_wait_time", "suggest_activities"])
        
        elif stage == JourneyStage.IN_VISIT:
            if not state.get("visit_started"):
                actions.extend(["start_visit", "generate_questions"])
        
        elif stage == JourneyStage.POST_VISIT:
            actions.extend(["create_post_visit_tasks", "generate_discharge"])
        
        elif stage == JourneyStage.DEPARTURE:
            actions.extend(["initiate_departure"])
    
    logger.info(f"Catchup actions from {current_stage} to {target_stage}: {actions}")
    
    return actions