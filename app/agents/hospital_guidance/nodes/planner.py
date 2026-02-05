import json
from app.agents.hospital_guidance.state import HospitalGuidanceState


def plan_next_steps(state: HospitalGuidanceState) -> HospitalGuidanceState:
    from app.services.llm_service import get_llm
    llm = get_llm()

    prompt = f"""
    You are a hospital workflow planner.

    Current journey stage: {state["journey_stage"].value}
    Current location: {state.get("detected_area")}
    User message: {state.get("user_message")}
    Check-in completed: {state.get("check_in_completed")}
    Visit started: {state.get("visit_started")}

    Decide the NEXT actions needed.
    Choose ONLY from this list:
    - handle_arrival
    - initiate_check_in
    - complete_check_in
    - provide_navigation
    - find_amenities
    - update_wait_time
    - suggest_activities
    - start_visit
    - handle_emergency
    - provide_support

    Return JSON:
    {
      "steps": ["step1", "step2"],
      "target_stage": "check_in | waiting | in_visit | post_visit"
    }
    """

    response = llm.invoke(prompt).content
    plan = json.loads(response)

    state["steps_pending"] = plan.get("steps", [])
    state["target_stage"] = plan.get("target_stage")
    state["autonomous_mode"] = True

    return state