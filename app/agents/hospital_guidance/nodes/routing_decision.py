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

# def llm_route_decision(state: HospitalGuidanceState) -> str:
#     """
#     Uses LLM to decide which route to take.
#     MUST return a string key that exists in conditional mapping.
#     """
    
#     user_message = state.get("user_message", "")
    
#     # Hard safety override for emergencies
#     if state.get("emergency_active"):
#         logger.info("Emergency active - routing to handle_emergency")
#         return "handle_emergency"
    
#     # Check for emergency keywords in message
#     if user_message:
#         emergency_keywords = ["emergency", "urgent", "help", "dying", "severe pain", "911", "can't breathe"]
#         if any(keyword in user_message.lower() for keyword in emergency_keywords):
#             logger.info("Emergency keywords detected - routing to detect_emergency")
#             return "detect_emergency"
    
#     # If no user message, provide support
#     if not user_message:
#         logger.warning("No user message provided - routing to provide_support")
#         return "provide_support"
    
#     # Enhanced prompt with examples for better routing
#     prompt = ChatPromptTemplate.from_template("""
# You are a hospital assistant router. Your job is to analyze the user's message and choose the most appropriate route.

# **Available Routes:**
# - provide_navigation: User wants directions to a SPECIFIC location (e.g., "How do I get to the cafeteria?", "Where is room 302?")
# - find_amenities: User wants to find NEARBY facilities without a specific destination (e.g., "Where's the nearest restroom?", "Is there a cafeteria nearby?")
# - update_wait_time: User asks about wait times or queue status (e.g., "How long is the wait?", "When will I be called?")
# - start_visit: User is beginning their appointment (e.g., "I'm here for my appointment", "Ready to see the doctor")
# - explain_term: User asks about medical terms or conditions (e.g., "What is hypertension?", "What does MRI mean?")
# - handle_arrival: User just arrived at hospital (e.g., "I just got here", "I'm at the entrance")
# - initiate_check_in: User wants to check in (e.g., "I need to check in", "Where do I register?")
# - create_post_visit_tasks: User finished their visit and needs next steps (e.g., "What do I do now?", "Do I need lab work?")
# - initiate_departure: User is ready to leave (e.g., "I'm leaving now", "How do I get out?")
# - provide_support: General questions or emotional support (e.g., "I'm nervous", "Can you help me?")
# - detect_emergency: Urgent medical situation (e.g., "I can't breathe", "Severe chest pain")

# **User Message:**
# "{message}"

# **Instructions:**
# 1. Analyze the user's intent
# 2. Choose the MOST SPECIFIC route that matches
# 3. Return ONLY the route name (no explanation, no quotes, no extra text)

# Route:""")
    
#     try:
#         llm = get_llm()
        
#         route = (
#             prompt
#             | llm
#             | StrOutputParser()
#         ).invoke({"message": user_message}).strip()
        
#         logger.info(f"LLM suggested route: '{route}' for message: '{user_message}'")
        
#         # Validate route
#         if route not in ALLOWED_ROUTES:
#             logger.warning(f"Invalid route from LLM: '{route}', falling back to provide_support")
#             return "provide_support"
        
#         return route
        
#     except Exception as e:
#         logger.error(f"Error in LLM routing: {e}, falling back to provide_support")
#         return "provide_support"

def llm_route_decision(state: HospitalGuidanceState) -> str:
    """
    Uses LLM to decide which route to take AND extract necessary data.
    MUST return a string key that exists in conditional mapping.
    """
    
    user_message = state.get("user_message", "")
    
    # Hard safety override for emergencies
    if state.get("emergency_active"):
        logger.info("Emergency active - routing to handle_emergency")
        return "handle_emergency"
    
    # Check for emergency keywords
    if user_message:
        emergency_keywords = ["emergency", "urgent", "help", "dying", "severe pain", "911", "can't breathe"]
        if any(keyword in user_message.lower() for keyword in emergency_keywords):
            logger.info("Emergency keywords detected - routing to detect_emergency")
            return "detect_emergency"
    
    if not user_message:
        logger.warning("No user message provided - routing to provide_support")
        return "provide_support"
    
    # Enhanced prompt for routing
    prompt = ChatPromptTemplate.from_template("""
You are a hospital assistant router analyzing patient requests.

**User Message:** "{message}"

**Your Task:**
1. Determine the patient's primary intent
2. Choose the most appropriate route from the list below
3. Return ONLY the route name (no explanation)

**Available Routes:**

**Navigation Routes:**
- provide_navigation: Patient wants directions to a SPECIFIC location
  Examples: "Where is the cafeteria?", "How do I get to room 302?", "Take me to the pharmacy"
  
- find_amenities: Patient wants to find NEARBY facilities (vague/general)
  Examples: "Where's the nearest restroom?", "Is there food nearby?", "ATM near me?"

**Wait & Queue Routes:**
- update_wait_time: Patient asks about wait times or their position in queue
  Examples: "How long is the wait?", "When will I be called?", "What's my queue position?"

**Visit Routes:**
- start_visit: Patient is beginning their appointment
  Examples: "I'm here for my appointment", "Ready to see the doctor", "I'm called in"
  
- explain_term: Patient asks about medical terms, conditions, or procedures
  Examples: "What is hypertension?", "What does MRI mean?", "Explain blood pressure"

**Journey Routes:**
- handle_arrival: Patient just arrived at the hospital
  Examples: "I just got here", "I'm at the entrance", "I arrived"
  
- initiate_check_in: Patient wants to check in or register
  Examples: "I need to check in", "Where do I register?", "Check-in process?"

**Post-Visit Routes:**
- create_post_visit_tasks: Patient finished visit and needs next steps
  Examples: "What do I do now?", "Do I need lab work?", "What's next after my appointment?"
  
- initiate_departure: Patient is ready to leave
  Examples: "I'm leaving now", "How do I exit?", "Where's the way out?"

**Support Routes:**
- provide_support: General questions, emotional support, or unclear intent
  Examples: "I'm nervous", "Can you help me?", "I have a question"
  
- detect_emergency: Urgent medical emergency
  Examples: "I can't breathe", "Severe chest pain", "Medical emergency"

**Instructions:**
Analyze the message and return ONLY the route name that best matches the patient's intent.

Route:""")
    
    try:
        llm = get_llm()
        
        route = (
            prompt 
            | llm 
            | StrOutputParser()
        ).invoke({"message": user_message}).strip()
        
        logger.info(f"LLM routing decision: '{route}' for message: '{user_message}'")
        
        # Validate
        if route not in ALLOWED_ROUTES:
            logger.warning(f"Invalid route '{route}' from LLM, using provide_support")
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