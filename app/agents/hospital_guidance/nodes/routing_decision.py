from typing import Any, Dict
from app.agents.hospital_guidance.state import HospitalGuidanceState
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser  # ← Add this
from app.services.llm_service import get_llm
import logging

logger = logging.getLogger(__name__)

ALLOWED_ROUTES = {
    "provide_navigation",
    "find_amenities",
    "update_wait_time",
    "start_visit",
    "explain_term",
    "handle_arrival",
    "initiate_check_in",
    "create_post_visit_tasks",
    "initiate_departure",
    "provide_support",
    "detect_emergency",
    "handle_emergency",
}

def llm_route_decision(state: HospitalGuidanceState) -> str:
    """
    Uses LLM to decide which route to take.
    MUST return a string key that exists in conditional mapping.
    """
    
    user_message = state.get("user_message", "")
    
    # Hard safety override for emergencies
    if state.get("emergency_active"):
        logger.info("Emergency active - routing to handle_emergency")
        return "handle_emergency"
    
    # Check for emergency keywords in message
    if user_message:
        emergency_keywords = ["emergency", "urgent", "help", "dying", "severe pain", "911", "can't breathe"]
        if any(keyword in user_message.lower() for keyword in emergency_keywords):
            logger.info("Emergency keywords detected - routing to detect_emergency")
            return "detect_emergency"
    
    # If no user message, provide support
    if not user_message:
        logger.warning("No user message provided - routing to provide_support")
        return "provide_support"
    
    # Enhanced prompt with examples for better routing
    prompt = ChatPromptTemplate.from_template("""
You are a hospital assistant router. Your job is to analyze the user's message and choose the most appropriate route.

**Available Routes:**
- provide_navigation: User wants directions to a SPECIFIC location (e.g., "How do I get to the cafeteria?", "Where is room 302?")
- find_amenities: User wants to find NEARBY facilities without a specific destination (e.g., "Where's the nearest restroom?", "Is there a cafeteria nearby?")
- update_wait_time: User asks about wait times or queue status (e.g., "How long is the wait?", "When will I be called?")
- start_visit: User is beginning their appointment (e.g., "I'm here for my appointment", "Ready to see the doctor")
- explain_term: User asks about medical terms or conditions (e.g., "What is hypertension?", "What does MRI mean?")
- handle_arrival: User just arrived at hospital (e.g., "I just got here", "I'm at the entrance")
- initiate_check_in: User wants to check in (e.g., "I need to check in", "Where do I register?")
- create_post_visit_tasks: User finished their visit and needs next steps (e.g., "What do I do now?", "Do I need lab work?")
- initiate_departure: User is ready to leave (e.g., "I'm leaving now", "How do I get out?")
- provide_support: General questions or emotional support (e.g., "I'm nervous", "Can you help me?")
- detect_emergency: Urgent medical situation (e.g., "I can't breathe", "Severe chest pain")

**User Message:**
"{message}"

**Instructions:**
1. Analyze the user's intent
2. Choose the MOST SPECIFIC route that matches
3. Return ONLY the route name (no explanation, no quotes, no extra text)

Route:""")
    
    try:
        llm = get_llm()
        
        route = (
            prompt
            | llm
            | StrOutputParser()
        ).invoke({"message": user_message}).strip()
        
        logger.info(f"LLM suggested route: '{route}' for message: '{user_message}'")
        
        # Validate route
        if route not in ALLOWED_ROUTES:
            logger.warning(f"Invalid route from LLM: '{route}', falling back to provide_support")
            return "provide_support"
        
        return route
        
    except Exception as e:
        logger.error(f"Error in LLM routing: {e}, falling back to provide_support")
        return "provide_support"


def route_request(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Initial routing node - passes state through with logging"""
    user_intent = state.get('user_intent')
    journey_stage = state.get('journey_stage')
    user_message = state.get('user_message', '')
    
    logger.info(
        f"Routing request | Intent: {user_intent} | Stage: {journey_stage} | "
        f"Message: '{user_message[:50]}...'" if len(user_message) > 50 else f"Message: '{user_message}'"
    )
    
    return state