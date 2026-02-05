# app/agents/hospital_guidance/nodes/executor.py

from typing import Dict, Any, Callable
import logging
from datetime import datetime

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.nodes import (
    arrival,
    navigation,
    queue_management,
    visit_assistance,
    post_visit,
    emergency
)

logger = logging.getLogger(__name__)

STEP_HANDLERS: Dict[str, Callable[[HospitalGuidanceState], HospitalGuidanceState]] = {
    "handle_arrival": arrival.handle_arrival,
    "initiate_check_in": arrival.initiate_check_in,
    "complete_check_in": arrival.complete_check_in,

    "update_wait_time": queue_management.update_wait_time,
    "suggest_activities": queue_management.suggest_activities_while_waiting,

    "start_visit": visit_assistance.start_visit,
    "generate_questions": visit_assistance.generate_question_prompts,
    "end_visit": visit_assistance.end_visit,

    "create_post_visit_tasks": post_visit.create_post_visit_tasks,
    "generate_discharge": post_visit.generate_discharge_instructions,
    "initiate_departure": post_visit.initiate_departure,
    "complete_journey": post_visit.complete_journey,
}


# =========================
# GUARDRAILS
# =========================

def is_step_allowed(step: str, state: HospitalGuidanceState) -> bool:
    """Prevent illegal transitions"""

    if step == "initiate_check_in" and state.get("journey_stage") != JourneyStage.ARRIVAL:
        return False

    if step == "complete_check_in" and not state.get("insurance_verified", True):
        return False

    if step == "start_visit" and not state.get("check_in_completed"):
        return False

    if step == "generate_discharge" and not state.get("visit_ended"):
        return False

    if step == "initiate_departure" and not state.get("visit_ended"):
        return False

    return True


# =========================
# EXECUTOR
# =========================

def execute_pending_steps(state: HospitalGuidanceState) -> HospitalGuidanceState:
    """
    Execute all pending autonomous steps.
    Supports:
    - Sequential execution
    - Parameterized steps
    - Mid-execution replanning
    """

    steps = state.get("steps_pending", [])

    if not steps:
        logger.info("No pending steps to execute")
        return state

    logger.info(f"Starting execution of {len(steps)} steps")

    # Process steps one-by-one (important for autonomy)
    while state.get("steps_pending"):

        step = state["steps_pending"].pop(0)
        logger.info(f"Executing step: {step}")

        # Emergency short-circuit
        if state.get("emergency_active") and step != "handle_emergency":
            logger.warning("Emergency active — skipping non-emergency steps")
            continue

        try:
            # ---------------------------
            # PARAMETERIZED STEPS
            # ---------------------------
            if isinstance(step, dict):
                action = step.get("action")

                if action == "navigate":
                    destination = step.get("destination")
                    if destination:
                        state = navigate_to(state, destination)
                    else:
                        logger.warning("Navigate step missing destination")

                elif action == "update_location":
                    new_location = create_location_from_area(state.get("detected_area"))
                    if new_location:
                        state = navigation.update_location(state, new_location)

                elif action == "handle_emergency":
                    state = emergency.handle_emergency(
                        state,
                        step.get("emergency_type", "general"),
                        step.get("user_message", "")
                    )

                else:
                    logger.warning(f"Unknown parameterized step: {step}")

                continue

            # ---------------------------
            # SIMPLE STRING STEPS
            # ---------------------------
            if not is_step_allowed(step, state):
                logger.warning(
                    f"Step '{step}' not allowed in stage {state.get('journey_stage')}"
                )
                continue

            handler = STEP_HANDLERS.get(step)

            if handler:
                state = handler(state)
            else:
                logger.warning(f"No handler registered for step: {step}")

        except Exception as e:
            logger.error(
                f"Error executing step '{step}': {str(e)}",
                exc_info=True
            )
            # Continue execution (fault tolerant)

    # Final bookkeeping
    state["last_updated"] = datetime.now()
    logger.info("All pending steps executed successfully")

    return state


# =========================
# HELPERS
# =========================

def navigate_to(state: HospitalGuidanceState, destination_name: str) -> HospitalGuidanceState:
    """Navigate patient to a named hospital destination"""

    from app.agents.hospital_guidance.tools.navigation_tool import navigation_tool

    destination = navigation_tool.find_location(destination_name)

    if not destination:
        logger.warning(f"Could not find destination: {destination_name}")
        return state

    if not state.get("current_location"):
        logger.warning("Current location unknown — cannot calculate route")
        return state

    route = navigation_tool.calculate_route(
        state["current_location"],
        destination
    )

    notification = {
        "type": "info",
        "title": f"Navigation to {destination['name']}",
        "message": f"Please proceed to {destination['name']}. "
                   f"{route['estimated_time'] // 60} minute walk.",
        "timestamp": datetime.now(),
        "route": route,
        "priority": "medium"
    }

    return {
        **state,
        "destination": destination,
        "navigation_route": route["steps"],
        "navigation_active": True,
        "target_stage": "pre_visit",
        "notifications": state.get("notifications", []) + [notification],
    }


def create_location_from_area(area: str) -> Dict[str, Any] | None:
    """Convert detected area into structured location"""

    if not area:
        return None

    from app.agents.hospital_guidance.tools.navigation_tool import navigation_tool

    area_map = {
        "entrance": "main entrance",
        "registration": "registration",
        "waiting_room": "waiting room",
        "exam_room": "exam room",
        "lab": "lab",
        "pharmacy": "pharmacy",
        "exit": "exit",
    }

    location_name = area_map.get(area)
    if not location_name:
        return None

    return navigation_tool.find_location(location_name)