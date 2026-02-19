import os
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
import logging
from datetime import datetime
import uuid

from app.models.hospital_models import (
    AppointmentInfo,
    InitializeJourneyRequest,
    UserInteractionRequest,
    NavigationRequest,
    LocationUpdateRequest,
    CheckInRequest,
    PrescriptionRequest,
    LabWorkRequest,
    FollowUpRequest,
    EmergencyRequest,
    FeedbackRequest,
    JourneyResponse,
    ConversationResponse,
    EmergencyResponse,
    SessionInfo,
    JourneyStageEnum
)
from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.agent import hospital_guidance_agent
from app.agents.hospital_guidance.nodes import (
    arrival,
    navigation,
    queue_management,
    visit_assistance,
    post_visit,
    emergency
)

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory session storage (in production, use Redis/database)
active_sessions: Dict[str, HospitalGuidanceState] = {}


def get_active_sessions() -> Dict[str, HospitalGuidanceState]:
    """Get reference to active sessions for use by other routers"""
    return active_sessions

# ===== SESSION MANAGEMENT =====

@router.post("/initialize", response_model=SessionInfo, status_code=status.HTTP_201_CREATED)
async def initialize_journey(request: InitializeJourneyRequest):
    """
    Initialize a new hospital journey session
    
    This creates a new session when a patient arrives at the hospital.
    """
    try:
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        # Create initial state
        initial_state: HospitalGuidanceState = {
            "session_id": session_id,
            "patient_id": request.patient_id,
            "hospital_id": request.hospital_id,
            "journey_stage": JourneyStage.ARRIVAL,
            "started_at": datetime.now(),
            
            # Appointment info
            "appointment_id": request.appointment_id,
            "doctor_name": request.doctor_name,
            "appointment_time": request.appointment_time,
            "department": request.department,
            "reason_for_visit": request.reason_for_visit,
            
            # Location
            "current_location": None,
            "destination": None,
            "navigation_active": False,
            "navigation_route": None,
            
            # Check-in status
            "check_in_completed": False,
            "insurance_verified": False,
            "forms_completed": False,
            "copay_paid": False,

            # Insurance details
            "insurance_details": None,
            "insurance_validation_errors": None,
            
            # Queue
            "queue_position": None,
            "estimated_wait_time": None,
            "last_wait_update": None,
            
            # Visit
            "visit_started": False,
            "visit_ended": False,
            "visit_summary": None,
            "diagnosis": None,
            "prescriptions": [],
            "tests_ordered": [],
            "follow_up_needed": False,
            "follow_up_date": None,
            
            # Tasks
            "pending_tasks": [],
            "completed_tasks": [],
            
            # Communications
            "notifications": [],
            "alerts": [],
            "family_notified": False,
            
            # Preferences
            "language": request.language,
            "accessibility_needs": request.accessibility_needs,
            "notification_preferences": {"sms": True, "email": True, "push": True},
            "family_contacts": request.family_contacts,
            
            # Interaction
            "conversation_history": [],
            "user_queries": [],
            "agent_responses": [],
            
            # Emergency
            "emergency_active": False,
            "emergency_type": None,
            "emergency_location": None,
            
            # Feedback
            "feedback_collected": False,
            "satisfaction_rating": None,
            
            # Metadata
            "last_updated": datetime.now(),
            "context": {}
        }
        
        # Run arrival handler
        result = arrival.handle_arrival(initial_state)
        
        # Store session
        active_sessions[session_id] = result
        
        logger.info(f"Initialized journey session {session_id} for patient {request.patient_id}")
        
        return SessionInfo(
            session_id=session_id,
            patient_id=request.patient_id,
            created_at=result["started_at"],
            last_activity=result["last_updated"],
            journey_stage=JourneyStageEnum(result["journey_stage"].value),
            active=True
        )
        
    except Exception as e:
        logger.error(f"Error initializing journey: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize journey: {str(e)}"
        )

@router.get("/session/{session_id}", response_model=JourneyResponse)
async def get_journey_status(session_id: str):
    """
    Get current journey status
    
    Returns the complete state of the patient's hospital journey.
    """
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    state = active_sessions[session_id]
    
    return _state_to_response(state)

@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_session(session_id: str):
    """
    End a journey session
    
    Called when patient leaves the hospital or session expires.
    """
    if session_id in active_sessions:
        logger.info(f"Ending session {session_id}")
        del active_sessions[session_id]
    
    return None

# ===== ARRIVAL & CHECK-IN =====

@router.post("/check-in/{session_id}", response_model=JourneyResponse)
async def complete_check_in(session_id: str, request: CheckInRequest):
    """
    Complete check-in process
    
    Handles insurance verification, form completion, and copay payment.
    """
    state = _get_session(session_id)
    
    try:
        # Process check-in
        result = arrival.complete_check_in(state)
        
        # Update session
        active_sessions[session_id] = result
        
        logger.info(f"Check-in completed for session {session_id}")
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error completing check-in: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete check-in: {str(e)}"
        )

# ===== NAVIGATION =====

@router.post("/navigate/{session_id}", response_model=JourneyResponse)
async def navigate_to_destination(session_id: str, request: NavigationRequest):
    """
    Get navigation to a destination
    
    Provides turn-by-turn directions from current location to destination.
    """
    state = _get_session(session_id)
    
    try:
        # Update state with navigation query
        state["navigation_query"] = request.destination_query
        
        # Get navigation
        result = navigation.provide_navigation(state, request.destination_query)
        
        # Update session
        active_sessions[session_id] = result
        
        logger.info(f"Navigation provided for session {session_id} to {request.destination_query}")
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error providing navigation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provide navigation: {str(e)}"
        )

@router.post("/location/{session_id}", response_model=JourneyResponse)
async def update_location(session_id: str, request: LocationUpdateRequest):
    """
    Update patient's current location
    
    Called when patient moves to a new location (automatic or manual update).
    """
    state = _get_session(session_id)
    
    try:
        result = navigation.update_location(state, request.location)
        
        active_sessions[session_id] = result
        
        logger.info(f"Location updated for session {session_id}")
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error updating location: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location: {str(e)}"
        )

@router.get("/amenities/{session_id}", response_model=JourneyResponse)
async def find_nearby_amenities(session_id: str):
    """
    Find nearby amenities (restrooms, cafeteria, etc.)
    
    Returns list of nearby amenities based on current location.
    """
    state = _get_session(session_id)
    
    try:
        result = navigation.find_nearby_amenities(state)
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error finding amenities: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find amenities: {str(e)}"
        )

# ===== QUEUE & WAIT MANAGEMENT =====

@router.get("/queue-status/{session_id}", response_model=JourneyResponse)
async def get_queue_status(session_id: str):
    """
    Get current queue position and wait time
    
    Returns updated queue information.
    """
    state = _get_session(session_id)
    
    try:
        result = queue_management.update_wait_time(state)
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue status: {str(e)}"
        )

@router.post("/notify-family/{session_id}")
async def notify_family(session_id: str, message: str):
    """
    Send notification to family members
    
    Sends the specified message to registered family contacts.
    """
    state = _get_session(session_id)
    
    try:
        result = queue_management.notify_family(state, message)
        
        active_sessions[session_id] = result
        
        return {"status": "success", "message": "Family notified"}
        
    except Exception as e:
        logger.error(f"Error notifying family: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to notify family: {str(e)}"
        )

# ===== VISIT ASSISTANCE =====

@router.post("/visit/start/{session_id}", response_model=JourneyResponse)
async def start_visit(session_id: str):
    """
    Mark visit as started
    
    Called when patient is called into exam room.
    """
    state = _get_session(session_id)
    
    try:
        result = visit_assistance.start_visit(state)
        
        active_sessions[session_id] = result
        
        logger.info(f"Visit started for session {session_id}")
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error starting visit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start visit: {str(e)}"
        )

@router.post("/visit/explain-term/{session_id}", response_model=ConversationResponse)
async def explain_medical_term(session_id: str, term: str):
    """
    Explain a medical term
    
    Provides patient-friendly explanation of medical terminology.
    """
    state = _get_session(session_id)
    
    try:
        result = visit_assistance.explain_medical_term(state, term)
        
        active_sessions[session_id] = result
        
        # Extract the explanation from notifications
        explanation = ""
        for notif in result.get("notifications", []):
            if notif.get("title", "").startswith("Medical Term:"):
                explanation = notif.get("message", "")
                break
        
        return ConversationResponse(
            session_id=session_id,
            response_message=explanation,
            intent_detected="explain_term",
            journey_updated=True,
            journey_stage=JourneyStageEnum(result["journey_stage"].value),
            notifications=_convert_notifications(result.get("notifications", []))
        )
        
    except Exception as e:
        logger.error(f"Error explaining term: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to explain term: {str(e)}"
        )

@router.post("/visit/prescription/{session_id}", response_model=JourneyResponse)
async def handle_prescription(session_id: str, request: PrescriptionRequest):
    """
    Record or route prescription
    
    Records new prescription or routes to pharmacy.
    """
    state = _get_session(session_id)
    
    try:
        if request.action == "record":
            result = visit_assistance.record_prescription(
                state,
                request.medication,
                request.dosage,
                request.frequency,
                request.instructions
            )
        elif request.action == "route":
            result = post_visit.handle_prescription_routing(
                state,
                request.pharmacy_choice.value if request.pharmacy_choice else "hospital"
            )
        else:
            raise ValueError(f"Invalid action: {request.action}")
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error handling prescription: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle prescription: {str(e)}"
        )

@router.post("/visit/lab-work/{session_id}", response_model=JourneyResponse)
async def handle_lab_work(session_id: str, request: LabWorkRequest):
    """
    Record or schedule lab work
    
    Records test order or schedules lab appointment.
    """
    state = _get_session(session_id)
    
    try:
        if request.action == "record":
            result = visit_assistance.record_test_order(
                state,
                request.test_name,
                request.test_type,
                request.urgency,
                request.test_instructions
            )
        elif request.action == "schedule":
            result = post_visit.schedule_lab_work(state, request.schedule_now)
        else:
            raise ValueError(f"Invalid action: {request.action}")
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error handling lab work: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle lab work: {str(e)}"
        )

@router.post("/visit/end/{session_id}", response_model=JourneyResponse)
async def end_visit(session_id: str):
    """
    Mark visit as complete
    
    Generates visit summary and transitions to post-visit stage.
    """
    state = _get_session(session_id)
    
    try:
        result = visit_assistance.end_visit(state)
        
        # Create post-visit tasks
        result = post_visit.create_post_visit_tasks(result)
        
        active_sessions[session_id] = result
        
        logger.info(f"Visit ended for session {session_id}")
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error ending visit: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end visit: {str(e)}"
        )

# ===== POST-VISIT =====

@router.post("/post-visit/follow-up/{session_id}", response_model=JourneyResponse)
async def schedule_follow_up(session_id: str, request: FollowUpRequest):
    """
    Schedule follow-up appointment
    
    Books next appointment with the doctor.
    """
    state = _get_session(session_id)
    
    try:
        result = post_visit.schedule_follow_up(state, request.preferred_date)
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error scheduling follow-up: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule follow-up: {str(e)}"
        )

@router.post("/post-visit/payment/{session_id}", response_model=JourneyResponse)
async def process_payment(session_id: str, payment_method: str):
    """
    Process payment/copay
    
    Handles billing and payment processing.
    """
    state = _get_session(session_id)
    
    try:
        result = post_visit.process_payment(state, payment_method)
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process payment: {str(e)}"
        )

@router.get("/discharge-instructions/{session_id}")
async def get_discharge_instructions(session_id: str):
    """
    Get discharge instructions
    
    Returns comprehensive post-visit care instructions.
    """
    state = _get_session(session_id)
    
    try:
        result = post_visit.generate_discharge_instructions(state)
        
        active_sessions[session_id] = result
        
        # Extract instructions from notifications
        instructions = ""
        for notif in result.get("notifications", []):
            if notif.get("type") == "discharge_instructions":
                instructions = notif.get("message", "")
                break
        
        return {
            "session_id": session_id,
            "instructions": instructions,
            "prescriptions": result.get("prescriptions", []),
            "tests_ordered": result.get("tests_ordered", []),
            "follow_up_date": result.get("follow_up_date")
        }
        
    except Exception as e:
        logger.error(f"Error getting discharge instructions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get discharge instructions: {str(e)}"
        )

@router.post("/departure/{session_id}", response_model=JourneyResponse)
async def initiate_departure(session_id: str):
    """
    Prepare for departure
    
    Checks pending tasks and guides patient to exit.
    """
    state = _get_session(session_id)
    
    try:
        result = post_visit.initiate_departure(state)
        
        active_sessions[session_id] = result
        
        return _state_to_response(result)
        
    except Exception as e:
        logger.error(f"Error initiating departure: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate departure: {str(e)}"
        )

# ===== EMERGENCY =====

@router.post("/emergency/{session_id}", response_model=EmergencyResponse)
async def report_emergency(session_id: str, request: EmergencyRequest):
    """
    Report emergency situation
    
    Immediately alerts hospital staff and activates emergency protocols.
    """
    state = _get_session(session_id)
    
    try:
        # Detect and handle emergency
        result = emergency.handle_emergency(
            state,
            request.emergency_type or "general",
            request.description
        )
        
        active_sessions[session_id] = result
        
        logger.critical(f"EMERGENCY reported for session {session_id}")
        
        # Find emergency notification
        emergency_notif = None
        for notif in result.get("notifications", []):
            if notif.get("type") == "emergency":
                emergency_notif = notif
                break
        
        return EmergencyResponse(
            session_id=session_id,
            emergency_active=result["emergency_active"],
            emergency_type=result["emergency_type"],
            message=emergency_notif.get("message", "") if emergency_notif else "",
            instructions=emergency_notif.get("instructions", []) if emergency_notif else [],
            staff_alerted=True,
            family_notified=result.get("family_notified", False),
            location=result.get("emergency_location", {}),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error handling emergency: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle emergency: {str(e)}"
        )

# ===== GENERAL INTERACTION =====

@router.post("/chat/{session_id}", response_model=ConversationResponse)
async def chat_with_agent(session_id: str, request: UserInteractionRequest):
    """
    General conversation with the agent
    
    Handles any user query or interaction.
    """
    state = _get_session(session_id)
    
    try:
        # Detect emergency in message
        emergency_result = emergency.detect_emergency(state, request.message)
        
        if emergency_result.get("emergency_active"):
            # Emergency detected!
            active_sessions[session_id] = emergency_result
            
            return ConversationResponse(
                session_id=session_id,
                response_message="🚨 EMERGENCY DETECTED - Medical staff have been alerted to your location. Help is on the way immediately.",
                intent_detected="emergency",
                journey_updated=True,
                journey_stage=JourneyStageEnum(emergency_result["journey_stage"].value),
                notifications=_convert_notifications(emergency_result.get("notifications", []))
            )
        
        # Use LLM to generate response based on context
        from app.services.llm_service import get_llm
        llm = get_llm()
        
        context_prompt = f"""
        You are a helpful hospital guidance assistant. A patient has asked:
        
        "{request.message}"
        
        Current context:
        - Journey stage: {state['journey_stage'].value}
        - Location: {state.get('current_location', {}).get('name', 'Unknown')}
        - Checked in: {state.get('check_in_completed', False)}
        - Queue position: {state.get('queue_position', 'N/A')}
        - Visit started: {state.get('visit_started', False)}
        
        Provide a helpful, friendly response. Keep it concise (2-3 sentences).
        """
        
        response = llm.invoke(context_prompt)
        response_message = response.content
        
        # Update conversation history
        state["conversation_history"].append({
            "timestamp": datetime.now(),
            "user_message": request.message,
            "agent_response": response_message
        })
        state["user_queries"].append(request.message)
        state["agent_responses"].append(response_message)
        state["last_updated"] = datetime.now()
        
        active_sessions[session_id] = state
        
        return ConversationResponse(
            session_id=session_id,
            response_message=response_message,
            intent_detected=request.intent,
            journey_updated=False,
            journey_stage=JourneyStageEnum(state["journey_stage"].value),
            notifications=[]
        )
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )

# ===== FEEDBACK =====

@router.post("/feedback/{session_id}")
async def submit_feedback(session_id: str, request: FeedbackRequest):
    """
    Submit feedback about the experience
    
    Collects patient satisfaction ratings and comments.
    """
    state = _get_session(session_id)
    
    try:
        state["feedback_collected"] = True
        state["satisfaction_rating"] = request.rating
        state["context"]["feedback_categories"] = request.categories
        state["context"]["feedback_comments"] = request.comments
        state["last_updated"] = datetime.now()
        
        active_sessions[session_id] = state
        
        logger.info(f"Feedback submitted for session {session_id}: {request.rating}/5")
        
        return {
            "status": "success",
            "message": "Thank you for your feedback!"
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )

# ===== HELPER FUNCTIONS =====

def _get_session(session_id: str) -> HospitalGuidanceState:
    """Get session or raise 404"""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return active_sessions[session_id]

def _state_to_response(state: HospitalGuidanceState) -> JourneyResponse:
    """Convert state to API response"""
    from app.models.hospital_models import (
        QueueStatus,
        Prescription,
        TestOrder,
        Task,
        LocationInfo,
        Amenity
    )
    
    # Build queue status
    queue_status = None
    if state.get("queue_position"):
        queue_status = QueueStatus(
            queue_position=state["queue_position"],
            estimated_wait_time=state.get("estimated_wait_time"),
            patients_ahead=state["queue_position"] - 1 if state["queue_position"] else None,
            last_updated=state.get("last_wait_update") or datetime.now()
        )
    
    # Convert location
    current_location = None
    if state.get("current_location"):
        loc = state["current_location"]
        current_location = LocationInfo(**loc)
    
    destination = None
    if state.get("destination"):
        dest = state["destination"]
        destination = LocationInfo(**dest)

    amenities = None
    if state.get("nearby_amenities"):
        amenities = [Amenity(**a) for a in state["nearby_amenities"]]
    
    current_appointment = None
    if state.get("appointment_id"):
        current_appointment = AppointmentInfo(
            appointment_id=state["appointment_id"],
            doctor_name=state["doctor_name"],
            appointment_time=state["appointment_time"],
            department=state.get("department", "General"),
            reason=state.get("reason_for_visit", ""),
            type="current",
            status="in_progress" if state.get("visit_started") else "scheduled",
            created_at=state.get("started_at", datetime.now())
        )
    
    # Convert follow-up appointment
    follow_up_appointment = None
    if state.get("follow_up_appointment"):
        follow_up = state["follow_up_appointment"]
        follow_up_appointment = AppointmentInfo(**follow_up)
    
    return JourneyResponse(
        session_id=state["session_id"],
        journey_stage=JourneyStageEnum(state["journey_stage"].value),
        patient_id=state["patient_id"],
        current_appointment=current_appointment,
        follow_up_appointment=follow_up_appointment,
        current_location=current_location,
        destination=destination,
        navigation_active=state.get("navigation_active", False),
        navigation_route=state.get("navigation_route"),
        nearby_amenities=amenities,
        amenities_last_updated=state.get("amenities_last_updated"),
        check_in_completed=state.get("check_in_completed", False),
        insurance_verified=state.get("insurance_verified", False),
        forms_completed=state.get("forms_completed", False),
        copay_paid=state.get("copay_paid", False),
        queue_status=queue_status,
        visit_started=state.get("visit_started", False),
        visit_ended=state.get("visit_ended", False),
        visit_summary=state.get("visit_summary"),
        diagnosis=state.get("diagnosis"),
        prescriptions=[Prescription(**p) for p in state.get("prescriptions", [])],
        tests_ordered=[TestOrder(**t) for t in state.get("tests_ordered", [])],
        pending_tasks=[Task(**t) for t in state.get("pending_tasks", [])],
        completed_tasks=state.get("completed_tasks", []),
        notifications=_convert_notifications(state.get("notifications", [])),
        emergency_active=state.get("emergency_active", False),
        last_updated=state["last_updated"]
    )

def _convert_notifications(notifications: list) -> list:
    """Convert notification dicts to Notification models"""
    from app.models.hospital_models import Notification
    
    result = []
    for notif in notifications:
        try:
            result.append(Notification(**notif))
        except Exception as e:
            logger.warning(f"Could not convert notification: {e}")
    
    return result

@router.post("/assist/{session_id}")
async def agent_assist(session_id: str, request: UserInteractionRequest):
    """
    Let the agent decide what to do based on user message
    Use this for:
    - Chat interface
    - Voice commands
    - Ambiguous requests
    """
    state = _get_session(session_id)
    
    # Add user input
    state["user_message"] = request.message
    state["user_intent"] = request.intent
    
    # LET AGENT DECIDE!
    result = hospital_guidance_agent.invoke(state)
    
    active_sessions[session_id] = result
    
    return ConversationResponse(
        session_id=session_id,
        response_message=_extract_agent_response(result),
        journey_updated=True,
        journey_stage=result["journey_stage"],
        notifications=result.get("notifications", [])
    )

def _extract_agent_response(state: HospitalGuidanceState) -> str:
    """Extract response message from agent result"""
    # Get latest notification
    if state.get("notifications"):
        return state["notifications"][-1].get("message", "")
    return "I'm here to help! What do you need?"
