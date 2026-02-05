# app/agents/hospital_guidance/autonomous_agent.py

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from enum import Enum

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.nodes import (
    arrival,
    navigation,
    queue_management,
    visit_assistance,
    post_visit,
    emergency
)
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions the agent can take"""
    # Arrival & Check-in
    HANDLE_ARRIVAL = "handle_arrival"
    INITIATE_CHECK_IN = "initiate_check_in"
    COMPLETE_CHECK_IN = "complete_check_in"
    
    # Navigation
    PROVIDE_NAVIGATION = "provide_navigation"
    FIND_AMENITIES = "find_amenities"
    UPDATE_LOCATION = "update_location"
    
    # Queue Management
    UPDATE_WAIT_TIME = "update_wait_time"
    SUGGEST_ACTIVITIES = "suggest_activities"
    NOTIFY_FAMILY = "notify_family"
    
    # Visit Assistance
    START_VISIT = "start_visit"
    EXPLAIN_MEDICAL_TERM = "explain_medical_term"
    CAPTURE_VISIT_NOTES = "capture_visit_notes"
    GENERATE_QUESTIONS = "generate_questions"
    RECORD_PRESCRIPTION = "record_prescription"
    RECORD_TEST_ORDER = "record_test_order"
    END_VISIT = "end_visit"
    
    # Post-Visit
    CREATE_POST_VISIT_TASKS = "create_post_visit_tasks"
    HANDLE_PRESCRIPTION_ROUTING = "handle_prescription_routing"
    SCHEDULE_LAB_WORK = "schedule_lab_work"
    SCHEDULE_FOLLOW_UP = "schedule_follow_up"
    PROCESS_PAYMENT = "process_payment"
    GENERATE_DISCHARGE_INSTRUCTIONS = "generate_discharge_instructions"
    INITIATE_DEPARTURE = "initiate_departure"
    COMPLETE_JOURNEY = "complete_journey"
    
    # Emergency
    DETECT_EMERGENCY = "detect_emergency"
    HANDLE_EMERGENCY = "handle_emergency"
    RESOLVE_EMERGENCY = "resolve_emergency"
    PROVIDE_EMOTIONAL_SUPPORT = "provide_emotional_support"
    
    # Communication
    SEND_MESSAGE = "send_message"
    NO_ACTION = "no_action"


class AutonomousHospitalAgent:
    """
    Fully autonomous agent that makes all decisions using LLM.
    
    The agent analyzes:
    - Current journey stage
    - Patient location and movement patterns
    - Time elapsed in each stage
    - User messages (if any)
    - Pending tasks
    - Context clues (appointments, wait times, etc.)
    
    And decides:
    - What actions to take
    - When to proactively help
    - How to respond to the user
    - What to execute next
    """
    
    def __init__(self):
        self.llm = get_llm()
        self.tools = self._create_tools()
        self.conversation_history: List[Any] = []
        
    def _create_tools(self) -> List[StructuredTool]:
        """Create all available tools for the agent"""
        
        tools = []
        
        # ===== ARRIVAL & CHECK-IN TOOLS =====
        
        class HandleArrivalInput(BaseModel):
            reason: str = Field(description="Why we're handling arrival now")
        
        tools.append(StructuredTool(
            name="handle_arrival",
            description="Initialize the patient's arrival at the hospital. Use this when a patient first enters the hospital.",
            func=lambda reason: {"action": "handle_arrival", "params": {}},
            args_schema=HandleArrivalInput
        ))
        
        class CompleteCheckInInput(BaseModel):
            reason: str = Field(description="Why check-in is being completed")
        
        tools.append(StructuredTool(
            name="complete_check_in",
            description="Complete the check-in process (insurance, forms, copay). Use when patient has reached reception and is ready to check in.",
            func=lambda reason: {"action": "complete_check_in", "params": {}},
            args_schema=CompleteCheckInInput
        ))
        
        # ===== NAVIGATION TOOLS =====
        
        class ProvideNavigationInput(BaseModel):
            destination: str = Field(description="Where the patient wants to go (e.g., 'cardiology department', 'waiting room', 'pharmacy')")
            reason: str = Field(description="Why navigation is needed")
        
        tools.append(StructuredTool(
            name="provide_navigation",
            description="Provide turn-by-turn navigation to a destination. Use when patient asks for directions or needs to go somewhere.",
            func=lambda destination, reason: {"action": "provide_navigation", "params": {"destination": destination}},
            args_schema=ProvideNavigationInput
        ))
        
        class FindAmenitiesInput(BaseModel):
            reason: str = Field(description="Why we're finding amenities")
        
        tools.append(StructuredTool(
            name="find_nearby_amenities",
            description="Find nearby amenities (restrooms, cafeteria, water fountains, ATM, etc.). Use when patient asks about facilities or has been waiting a long time.",
            func=lambda reason: {"action": "find_amenities", "params": {}},
            args_schema=FindAmenitiesInput
        ))
        
        # ===== QUEUE MANAGEMENT TOOLS =====
        
        class UpdateWaitTimeInput(BaseModel):
            reason: str = Field(description="Why we're updating wait time")
        
        tools.append(StructuredTool(
            name="update_wait_time",
            description="Get the current queue position and estimated wait time. Use proactively every 5-10 minutes during waiting, or when patient asks.",
            func=lambda reason: {"action": "update_wait_time", "params": {}},
            args_schema=UpdateWaitTimeInput
        ))
        
        class SuggestActivitiesInput(BaseModel):
            reason: str = Field(description="Why we're suggesting activities")
        
        tools.append(StructuredTool(
            name="suggest_activities",
            description="Suggest activities while waiting (reading materials, cafeteria, etc.). Use when wait time is long (>15 min).",
            func=lambda reason: {"action": "suggest_activities", "params": {}},
            args_schema=SuggestActivitiesInput
        ))
        
        class NotifyFamilyInput(BaseModel):
            message: str = Field(description="Message to send to family members")
            reason: str = Field(description="Why we're notifying family")
        
        tools.append(StructuredTool(
            name="notify_family",
            description="Send notification to family members. Use when patient requests it or during emergencies.",
            func=lambda message, reason: {"action": "notify_family", "params": {"message": message}},
            args_schema=NotifyFamilyInput
        ))
        
        # ===== VISIT ASSISTANCE TOOLS =====
        
        class StartVisitInput(BaseModel):
            reason: str = Field(description="Why visit is starting")
        
        tools.append(StructuredTool(
            name="start_visit",
            description="Mark that the patient's visit with the doctor has started. Use when patient enters exam room or doctor calls them.",
            func=lambda reason: {"action": "start_visit", "params": {}},
            args_schema=StartVisitInput
        ))
        
        class ExplainMedicalTermInput(BaseModel):
            term: str = Field(description="Medical term to explain")
        
        tools.append(StructuredTool(
            name="explain_medical_term",
            description="Explain a medical term in patient-friendly language. Use when patient asks about medical terminology.",
            func=lambda term: {"action": "explain_medical_term", "params": {"term": term}},
            args_schema=ExplainMedicalTermInput
        ))
        
        class RecordPrescriptionInput(BaseModel):
            medication: str = Field(description="Name of medication")
            dosage: str = Field(description="Dosage (e.g., '500mg')")
            frequency: str = Field(description="Frequency (e.g., 'twice daily')")
            instructions: str = Field(description="Additional instructions")
        
        tools.append(StructuredTool(
            name="record_prescription",
            description="Record a prescription given by the doctor. Use when doctor prescribes medication.",
            func=lambda medication, dosage, frequency, instructions: {
                "action": "record_prescription",
                "params": {"medication": medication, "dosage": dosage, "frequency": frequency, "instructions": instructions}
            },
            args_schema=RecordPrescriptionInput
        ))
        
        class RecordTestOrderInput(BaseModel):
            test_name: str = Field(description="Name of the test")
            test_type: str = Field(description="Type of test (blood, imaging, etc.)")
            urgency: str = Field(description="Urgency level")
            instructions: str = Field(description="Test instructions")
        
        tools.append(StructuredTool(
            name="record_test_order",
            description="Record a lab test or imaging order. Use when doctor orders tests.",
            func=lambda test_name, test_type, urgency, instructions: {
                "action": "record_test_order",
                "params": {"test_name": test_name, "test_type": test_type, "urgency": urgency, "instructions": instructions}
            },
            args_schema=RecordTestOrderInput
        ))
        
        class EndVisitInput(BaseModel):
            reason: str = Field(description="Why visit is ending")
        
        tools.append(StructuredTool(
            name="end_visit",
            description="Mark the visit as complete and generate summary. Use when doctor finishes consultation.",
            func=lambda reason: {"action": "end_visit", "params": {}},
            args_schema=EndVisitInput
        ))
        
        # ===== POST-VISIT TOOLS =====
        
        class ScheduleFollowUpInput(BaseModel):
            preferred_date: Optional[str] = Field(default=None, description="Preferred follow-up date")
        
        tools.append(StructuredTool(
            name="schedule_follow_up",
            description="Schedule a follow-up appointment. Use when doctor recommends follow-up or patient requests it.",
            func=lambda preferred_date=None: {"action": "schedule_follow_up", "params": {"preferred_date": preferred_date}},
            args_schema=ScheduleFollowUpInput
        ))
        
        class HandlePrescriptionRoutingInput(BaseModel):
            pharmacy_choice: str = Field(description="Pharmacy choice: 'hospital' or 'external'")
        
        tools.append(StructuredTool(
            name="handle_prescription_routing",
            description="Route prescription to pharmacy. Use after visit ends if prescriptions were given.",
            func=lambda pharmacy_choice: {"action": "handle_prescription_routing", "params": {"pharmacy_choice": pharmacy_choice}},
            args_schema=HandlePrescriptionRoutingInput
        ))
        
        class ScheduleLabWorkInput(BaseModel):
            schedule_now: bool = Field(description="Whether to schedule for today or later")
        
        tools.append(StructuredTool(
            name="schedule_lab_work",
            description="Schedule lab work or imaging. Use after visit if tests were ordered.",
            func=lambda schedule_now: {"action": "schedule_lab_work", "params": {"schedule_now": schedule_now}},
            args_schema=ScheduleLabWorkInput
        ))
        
        class ProcessPaymentInput(BaseModel):
            payment_method: str = Field(description="Payment method (card, cash, insurance)")
        
        tools.append(StructuredTool(
            name="process_payment",
            description="Process payment or copay. Use before patient leaves.",
            func=lambda payment_method: {"action": "process_payment", "params": {"payment_method": payment_method}},
            args_schema=ProcessPaymentInput
        ))
        
        class GenerateDischargeInput(BaseModel):
            reason: str = Field(description="Why generating discharge instructions")
        
        tools.append(StructuredTool(
            name="generate_discharge_instructions",
            description="Generate comprehensive discharge instructions. Use before patient leaves.",
            func=lambda reason: {"action": "generate_discharge_instructions", "params": {}},
            args_schema=GenerateDischargeInput
        ))
        
        class InitiateDepartureInput(BaseModel):
            reason: str = Field(description="Why initiating departure")
        
        tools.append(StructuredTool(
            name="initiate_departure",
            description="Prepare patient for departure, check pending tasks. Use when all tasks are complete and patient is ready to leave.",
            func=lambda reason: {"action": "initiate_departure", "params": {}},
            args_schema=InitiateDepartureInput
        ))
        
        # ===== EMERGENCY TOOLS =====
        
        class HandleEmergencyInput(BaseModel):
            emergency_type: str = Field(description="Type of emergency")
            description: str = Field(description="Description of the emergency")
        
        tools.append(StructuredTool(
            name="handle_emergency",
            description="CRITICAL: Handle emergency situation. Use immediately if patient reports pain, distress, or emergency.",
            func=lambda emergency_type, description: {
                "action": "handle_emergency",
                "params": {"emergency_type": emergency_type, "description": description}
            },
            args_schema=HandleEmergencyInput
        ))
        
        class ProvideEmotionalSupportInput(BaseModel):
            concern: str = Field(description="Patient's concern or worry")
        
        tools.append(StructuredTool(
            name="provide_emotional_support",
            description="Provide emotional support and reassurance. Use when patient expresses anxiety or concern.",
            func=lambda concern: {"action": "provide_emotional_support", "params": {"concern": concern}},
            args_schema=ProvideEmotionalSupportInput
        ))
        
        # ===== COMMUNICATION TOOL =====
        
        class SendMessageInput(BaseModel):
            message: str = Field(description="Message to send to the patient")
        
        tools.append(StructuredTool(
            name="send_message",
            description="Send a message to the patient. Use for general communication, updates, or responses.",
            func=lambda message: {"action": "send_message", "params": {"message": message}},
            args_schema=SendMessageInput
        ))
        
        return tools
    
    def _build_context_summary(self, state: HospitalGuidanceState) -> str:
        """Build a comprehensive context summary for the LLM"""
        
        journey_stage = state.get("journey_stage", JourneyStage.ARRIVAL)
        current_location = state.get("current_location", {})
        
        # Calculate time in current stage
        last_updated = state.get("last_updated", datetime.now())
        started_at = state.get("started_at", datetime.now())
        time_elapsed = (datetime.now() - started_at).total_seconds() / 60  # minutes
        
        context = f"""
CURRENT SITUATION:
- Journey Stage: {journey_stage.value}
- Time Elapsed: {time_elapsed:.0f} minutes since arrival
- Current Location: {current_location.get('name', 'Unknown')} ({current_location.get('type', 'unknown')})
- Patient ID: {state.get('patient_id', 'unknown')}

APPOINTMENT DETAILS:
- Doctor: {state.get('doctor_name', 'N/A')}
- Department: {state.get('department', 'N/A')}
- Appointment Time: {state.get('appointment_time', 'N/A')}
- Reason: {state.get('reason_for_visit', 'N/A')}

CHECK-IN STATUS:
- Check-in Completed: {state.get('check_in_completed', False)}
- Insurance Verified: {state.get('insurance_verified', False)}
- Forms Completed: {state.get('forms_completed', False)}
- Copay Paid: {state.get('copay_paid', False)}

QUEUE STATUS:
- Position: {state.get('queue_position', 'N/A')}
- Estimated Wait: {state.get('estimated_wait_time', 'N/A')}
- Last Update: {state.get('last_wait_update', 'N/A')}

VISIT STATUS:
- Visit Started: {state.get('visit_started', False)}
- Visit Ended: {state.get('visit_ended', False)}
- Diagnosis: {state.get('diagnosis', 'N/A')}
- Prescriptions: {len(state.get('prescriptions', []))} prescription(s)
- Tests Ordered: {len(state.get('tests_ordered', []))} test(s)
- Follow-up Needed: {state.get('follow_up_needed', False)}

PENDING TASKS:
{self._format_tasks(state.get('pending_tasks', []))}

COMPLETED TASKS:
{len(state.get('completed_tasks', []))} task(s) completed

NAVIGATION:
- Navigation Active: {state.get('navigation_active', False)}
- Destination: {state.get('destination', {}).get('name', 'None')}

EMERGENCY:
- Emergency Active: {state.get('emergency_active', False)}

PATIENT PREFERENCES:
- Language: {state.get('language', 'English')}
- Accessibility Needs: {state.get('accessibility_needs', [])}
"""
        
        return context.strip()
    
    def _format_tasks(self, tasks: List[Dict]) -> str:
        """Format pending tasks for context"""
        if not tasks:
            return "- No pending tasks"
        
        return "\n".join([f"- [{t.get('priority', 'normal')}] {t.get('description', 'Unknown task')}" for t in tasks])
    
    def _detect_location_triggers(self, state: HospitalGuidanceState) -> List[str]:
        """Detect location-based triggers that should prompt actions"""
        
        triggers = []
        current_location = state.get("current_location", {})
        location_type = current_location.get("type", "")
        location_name = current_location.get("name", "")
        journey_stage = state.get("journey_stage", JourneyStage.ARRIVAL)
        
        # Arrival triggers
        if location_type == "entrance" and journey_stage == JourneyStage.ARRIVAL:
            if not state.get("check_in_completed"):
                triggers.append("Patient at entrance - should guide to reception for check-in")
        
        # Reception triggers
        if location_type == "reception" and not state.get("check_in_completed"):
            triggers.append("Patient at reception - should initiate check-in process")
        
        # Waiting room triggers
        if location_type == "waiting_room" and state.get("check_in_completed"):
            wait_time = state.get("estimated_wait_time")
            if wait_time and wait_time > 15:
                triggers.append(f"Patient waiting for {wait_time} minutes - consider suggesting activities or amenities")
        
        # Department/Exam room triggers
        if location_type in ["department", "exam_room"]:
            if not state.get("visit_started") and state.get("check_in_completed"):
                triggers.append("Patient in department/exam room - visit should start")
        
        # Pharmacy triggers
        if location_type == "pharmacy" and state.get("prescriptions"):
            triggers.append("Patient at pharmacy - help with prescription pickup")
        
        # Lab triggers
        if location_type == "lab" and state.get("tests_ordered"):
            triggers.append("Patient at lab - help with test procedures")
        
        # Exit triggers
        if location_type == "exit" and state.get("visit_ended"):
            if state.get("pending_tasks"):
                triggers.append("Patient at exit with pending tasks - remind before departure")
        
        return triggers
    
    def _create_system_prompt(self, state: HospitalGuidanceState, location_triggers: List[str]) -> str:
        """Create the system prompt for the agent"""
        
        system_prompt = """You are an intelligent hospital guidance assistant helping patients navigate their entire hospital visit.

Your role is to:
1. PROACTIVELY guide patients through their journey based on their location and context
2. RESPOND to patient questions and concerns
3. ANTICIPATE patient needs before they ask
4. ENSURE smooth transitions between journey stages
5. HANDLE emergencies immediately

DECISION-MAKING FRAMEWORK:

1. ALWAYS check for emergencies first - if patient mentions pain, distress, or emergency, use handle_emergency immediately
2. Analyze the current context (location, journey stage, time elapsed, pending tasks)
3. Look for location-based triggers that should prompt actions
4. Decide if proactive action is needed OR just respond to user message
5. Choose appropriate tools to execute actions
6. Send clear, friendly messages to keep patient informed

PROACTIVE BEHAVIORS:

- When patient enters hospital → handle_arrival
- When patient reaches reception → complete_check_in
- When patient needs to go somewhere → provide_navigation
- When waiting >10 minutes → update_wait_time
- When waiting >20 minutes → suggest_activities or find_nearby_amenities
- When patient enters exam room → start_visit
- When visit ends → create post-visit tasks, handle prescriptions/labs
- When all tasks complete → initiate_departure
- When patient asks about anything medical → explain clearly and offer to explain_medical_term if needed

RESPONSE STYLE:
- Be warm, friendly, and professional
- Use simple language (avoid medical jargon unless explaining terms)
- Be proactive but not overwhelming
- Acknowledge patient concerns
- Provide clear next steps
- Keep messages concise (2-3 sentences usually)

CURRENT CONTEXT:
{context}

LOCATION-BASED TRIGGERS:
{triggers}

Now, based on the current situation and any user message, decide what actions to take using the available tools.
"""
        
        context = self._build_context_summary(state)
        triggers_text = "\n".join([f"- {t}" for t in location_triggers]) if location_triggers else "- No specific location triggers"
        
        return system_prompt.format(context=context, triggers=triggers_text)
    
    async def process_input(
        self,
        state: HospitalGuidanceState,
        user_message: Optional[str] = None,
        location_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point - process any input and decide what to do.
        
        Args:
            state: Current journey state
            user_message: Optional message from user
            location_update: Optional location update from frontend
            
        Returns:
            Dict with actions to execute and response message
        """
        
        try:
            # Update location if provided
            if location_update:
                state = self._update_location_in_state(state, location_update)
            
            # Detect location-based triggers
            location_triggers = self._detect_location_triggers(state)
            
            # Build system prompt
            system_prompt = self._create_system_prompt(state, location_triggers)
            
            # Build user message
            if user_message:
                user_msg = f"USER MESSAGE: {user_message}"
            elif location_update:
                user_msg = f"LOCATION UPDATE: Patient moved to {location_update.get('name', 'unknown location')}"
            else:
                user_msg = "PROACTIVE CHECK: Analyze current situation and take appropriate actions."
            
            # Create messages for LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_msg)
            ]
            
            # Get LLM to decide actions using tools
            llm_with_tools = self.llm.bind_tools(self.tools)
            response = llm_with_tools.invoke(messages)
            
            # Extract actions and text response
            actions_to_execute = []
            response_message = ""
            
            # Check if LLM used any tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    action_info = tool_call.get('function', {})
                    actions_to_execute.append(action_info)
            
            # Get text response
            if hasattr(response, 'content'):
                response_message = response.content
            
            # If no tools used but there's a message, create a send_message action
            if not actions_to_execute and response_message:
                actions_to_execute.append({
                    "action": "send_message",
                    "params": {"message": response_message}
                })
            
            logger.info(f"Agent decided on {len(actions_to_execute)} action(s): {[a.get('action') for a in actions_to_execute]}")
            
            return {
                "actions": actions_to_execute,
                "response_message": response_message,
                "reasoning": "LLM-driven decision based on context",
                "location_triggers": location_triggers
            }
            
        except Exception as e:
            logger.error(f"Error in autonomous agent processing: {str(e)}", exc_info=True)
            return {
                "actions": [{
                    "action": "send_message",
                    "params": {"message": "I'm here to help! How can I assist you today?"}
                }],
                "response_message": "I'm here to help! How can I assist you today?",
                "error": str(e)
            }
    
    def _update_location_in_state(
        self,
        state: HospitalGuidanceState,
        location_update: Dict[str, Any]
    ) -> HospitalGuidanceState:
        """Update the state with new location information"""
        
        previous_location = state.get("current_location")
        state["current_location"] = location_update
        state["last_updated"] = datetime.now()
        
        # Track location history
        if "location_history" not in state:
            state["location_history"] = []
        
        state["location_history"].append({
            "location": location_update,
            "timestamp": datetime.now(),
            "previous_location": previous_location
        })
        
        logger.info(f"Location updated to: {location_update.get('name', 'unknown')}")
        
        return state
    
    def execute_actions(
        self,
        state: HospitalGuidanceState,
        actions: List[Dict[str, Any]]
    ) -> HospitalGuidanceState:
        """
        Execute the list of actions decided by the agent.
        
        Args:
            state: Current state
            actions: List of actions to execute
            
        Returns:
            Updated state after all actions
        """
        
        for action_info in actions:
            action_name = action_info.get("action")
            params = action_info.get("params", {})
            
            logger.info(f"Executing action: {action_name} with params: {params}")
            
            try:
                state = self._execute_single_action(state, action_name, params)
            except Exception as e:
                logger.error(f"Error executing action {action_name}: {str(e)}", exc_info=True)
                # Add error notification but continue
                state.setdefault("notifications", []).append({
                    "type": "error",
                    "title": "Action Failed",
                    "message": f"Could not complete: {action_name}",
                    "timestamp": datetime.now()
                })
        
        return state
    
    def _execute_single_action(
        self,
        state: HospitalGuidanceState,
        action_name: str,
        params: Dict[str, Any]
    ) -> HospitalGuidanceState:
        """Execute a single action"""
        
        # Map action names to actual functions
        action_map = {
            # Arrival
            "handle_arrival": arrival.handle_arrival,
            "complete_check_in": arrival.complete_check_in,
            
            # Navigation
            "provide_navigation": lambda s: navigation.provide_navigation(s, params.get("destination", "")),
            "find_amenities": navigation.find_nearby_amenities,
            "update_location": lambda s: navigation.update_location(s, params.get("location", {})),
            
            # Queue
            "update_wait_time": queue_management.update_wait_time,
            "suggest_activities": queue_management.suggest_activities_while_waiting,
            "notify_family": lambda s: queue_management.notify_family(s, params.get("message", "")),
            
            # Visit
            "start_visit": visit_assistance.start_visit,
            "explain_medical_term": lambda s: visit_assistance.explain_medical_term(s, params.get("term", "")),
            "capture_visit_notes": lambda s: visit_assistance.capture_visit_notes(s, params.get("notes", "")),
            "generate_questions": visit_assistance.generate_question_prompts,
            "record_prescription": lambda s: visit_assistance.record_prescription(
                s,
                params.get("medication", ""),
                params.get("dosage", ""),
                params.get("frequency", ""),
                params.get("instructions", "")
            ),
            "record_test_order": lambda s: visit_assistance.record_test_order(
                s,
                params.get("test_name", ""),
                params.get("test_type", ""),
                params.get("urgency", ""),
                params.get("instructions", "")
            ),
            "end_visit": visit_assistance.end_visit,
            
            # Post-visit
            "create_post_visit_tasks": post_visit.create_post_visit_tasks,
            "handle_prescription_routing": lambda s: post_visit.handle_prescription_routing(
                s, params.get("pharmacy_choice", "hospital")
            ),
            "schedule_lab_work": lambda s: post_visit.schedule_lab_work(s, params.get("schedule_now", True)),
            "schedule_follow_up": lambda s: post_visit.schedule_follow_up(s, params.get("preferred_date")),
            "process_payment": lambda s: post_visit.process_payment(s, params.get("payment_method", "card")),
            "generate_discharge_instructions": post_visit.generate_discharge_instructions,
            "initiate_departure": post_visit.initiate_departure,
            "complete_journey": post_visit.complete_journey,
            
            # Emergency
            "handle_emergency": lambda s: emergency.handle_emergency(
                s,
                params.get("emergency_type", "general"),
                params.get("description", "")
            ),
            "provide_emotional_support": lambda s: emergency.provide_emotional_support(
                s, params.get("concern", "")
            ),
            
            # Communication
            "send_message": lambda s: self._add_message_to_state(s, params.get("message", ""))
        }
        
        # Execute the action
        if action_name in action_map:
            return action_map[action_name](state)
        else:
            logger.warning(f"Unknown action: {action_name}")
            return state
    
    def _add_message_to_state(self, state: HospitalGuidanceState, message: str) -> HospitalGuidanceState:
        """Add a message to state notifications"""
        
        state.setdefault("notifications", []).append({
            "type": "info",
            "title": "Assistant",
            "message": message,
            "timestamp": datetime.now()
        })
        
        return state


# Create singleton instance
autonomous_agent = AutonomousHospitalAgent()