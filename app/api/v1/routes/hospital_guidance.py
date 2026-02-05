# app/routers/hospital_autonomous.py

"""
Autonomous Hospital Guidance API

Single unified endpoint - the LLM agent makes ALL decisions.
Frontend only needs to call one endpoint with context updates.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import uuid

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.agent import autonomous_agent
from app.models.hospital_models import (
    JourneyStageEnum,
    Notification,
    SessionInfo
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/autonomous", tags=["Autonomous Hospital Guidance"])

# In-memory session storage
active_sessions: Dict[str, HospitalGuidanceState] = {}


# ===== REQUEST/RESPONSE MODELS =====

class LocationUpdate(BaseModel):
    """Location information from frontend"""
    name: str = Field(..., description="Name of the location")
    type: str = Field(..., description="Type: entrance, reception, waiting_room, department, exam_room, pharmacy, lab, exit, etc.")
    floor: Optional[int] = Field(None, description="Floor number")
    building: Optional[str] = Field(None, description="Building name")
    coordinates: Optional[Dict[str, float]] = Field(None, description="GPS or indoor coordinates")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional location metadata")


class AutonomousInput(BaseModel):
    """
    Unified input model - frontend sends ANY combination of these fields.
    The agent decides what to do based on all available context.
    """
    # User interaction (optional)
    user_message: Optional[str] = Field(None, description="Message from user (voice, text, or button click)")
    
    # Location update (optional)
    location: Optional[LocationUpdate] = Field(None, description="Current location of patient")
    
    # Context hints (optional)
    context_hints: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context from frontend (e.g., button clicked, time spent, etc.)"
    )
    
    # Force action (optional - use sparingly)
    force_action: Optional[str] = Field(
        None,
        description="Force a specific action (emergency use only)"
    )


class AgentAction(BaseModel):
    """Action decided by the agent"""
    action: str
    params: Dict[str, Any]
    reasoning: Optional[str] = None


class AutonomousResponse(BaseModel):
    """Response from the autonomous agent"""
    session_id: str
    journey_stage: JourneyStageEnum
    
    # What the agent did
    actions_taken: List[AgentAction]
    
    # Message to display to user
    message: str
    
    # Updated state information
    current_location: Optional[Dict[str, Any]] = None
    queue_position: Optional[int] = None
    estimated_wait_time: Optional[int] = None
    pending_tasks: List[Dict[str, Any]] = Field(default_factory=list)
    completed_tasks: List[str] = Field(default_factory=list)
    
    # Notifications
    notifications: List[Notification] = Field(default_factory=list)
    
    # Navigation
    navigation_active: bool = False
    navigation_route: Optional[Dict[str, Any]] = None
    destination: Optional[Dict[str, Any]] = None
    
    # Visit info
    visit_started: bool = False
    visit_ended: bool = False
    prescriptions_count: int = 0
    tests_ordered_count: int = 0
    
    # Emergency
    emergency_active: bool = False
    
    # Metadata
    timestamp: datetime
    agent_reasoning: Optional[str] = None


class InitializeAutonomousRequest(BaseModel):
    """Initialize a new autonomous journey"""
    patient_id: str
    hospital_id: str
    
    # Appointment info
    appointment_id: Optional[str] = None
    doctor_name: Optional[str] = None
    appointment_time: Optional[datetime] = None
    department: Optional[str] = None
    reason_for_visit: Optional[str] = None
    
    # Preferences
    language: str = "English"
    accessibility_needs: List[str] = Field(default_factory=list)
    family_contacts: List[Dict[str, str]] = Field(default_factory=list)
    
    # Initial location (optional)
    initial_location: Optional[LocationUpdate] = None


# ===== API ENDPOINTS =====

@router.post("/initialize", response_model=SessionInfo, status_code=status.HTTP_201_CREATED)
async def initialize_autonomous_journey(request: InitializeAutonomousRequest):
    """
    Initialize a new autonomous hospital journey.
    
    This creates a session and the agent immediately takes over.
    The agent will guide the patient through their entire visit.
    """
    try:
        session_id = f"auto_{uuid.uuid4().hex[:12]}"
        
        # Create initial state
        initial_state: HospitalGuidanceState = {
            "session_id": session_id,
            "patient_id": request.patient_id,
            "hospital_id": request.hospital_id,
            "journey_stage": JourneyStage.ARRIVAL,
            "started_at": datetime.now(),
            
            # Appointment
            "appointment_id": request.appointment_id,
            "doctor_name": request.doctor_name,
            "appointment_time": request.appointment_time,
            "department": request.department,
            "reason_for_visit": request.reason_for_visit,
            
            # Location
            "current_location": request.initial_location.dict() if request.initial_location else None,
            "destination": None,
            "navigation_active": False,
            "navigation_route": None,
            
            # Status
            "check_in_completed": False,
            "insurance_verified": False,
            "forms_completed": False,
            "copay_paid": False,
            "queue_position": None,
            "estimated_wait_time": None,
            "last_wait_update": None,
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
            
            # Metadata
            "last_updated": datetime.now(),
            "context": {}
        }
        
        # Let agent handle arrival
        agent_decision = await autonomous_agent.process_input(
            initial_state,
            user_message="Patient has arrived at the hospital",
            location_update=request.initial_location.dict() if request.initial_location else None
        )
        
        # Execute agent's decisions
        updated_state = autonomous_agent.execute_actions(
            initial_state,
            agent_decision.get("actions", [])
        )
        
        # Store session
        active_sessions[session_id] = updated_state
        
        logger.info(f"Initialized autonomous journey {session_id} for patient {request.patient_id}")
        
        return SessionInfo(
            session_id=session_id,
            patient_id=request.patient_id,
            created_at=updated_state["started_at"],
            last_activity=updated_state["last_updated"],
            journey_stage=JourneyStageEnum(updated_state["journey_stage"].value),
            active=True
        )
        
    except Exception as e:
        logger.error(f"Error initializing autonomous journey: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize journey: {str(e)}"
        )


@router.post("/interact/{session_id}", response_model=AutonomousResponse)
async def interact_with_agent(session_id: str, input_data: AutonomousInput):
    """
    🎯 MAIN ENDPOINT - The only endpoint frontend needs to call!
    
    Send ANY combination of:
    - User message (voice, text, button)
    - Location update
    - Context hints
    
    The agent will:
    1. Analyze ALL available context
    2. Detect location-based triggers
    3. Understand user intent
    4. Decide what actions to take
    5. Execute those actions
    6. Return comprehensive response
    
    Examples:
    
    1. Location update only:
       POST /interact/{session_id}
       {"location": {"name": "Reception", "type": "reception"}}
       → Agent detects patient at reception, initiates check-in
    
    2. User message only:
       POST /interact/{session_id}
       {"user_message": "Where is the bathroom?"}
       → Agent provides navigation to nearest restroom
    
    3. Both:
       POST /interact/{session_id}
       {
         "user_message": "I'm feeling anxious",
         "location": {"name": "Waiting Room", "type": "waiting_room"}
       }
       → Agent provides emotional support + suggests activities while waiting
    
    4. No input (proactive check):
       POST /interact/{session_id}
       {}
       → Agent analyzes current state, takes proactive actions if needed
    """
    
    # Get session
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    state = active_sessions[session_id]
    
    try:
        # Let the agent decide what to do!
        agent_decision = await autonomous_agent.process_input(
            state,
            user_message=input_data.user_message,
            location_update=input_data.location.dict() if input_data.location else None
        )
        
        # Execute agent's decisions
        updated_state = autonomous_agent.execute_actions(
            state,
            agent_decision.get("actions", [])
        )
        
        # Update session
        active_sessions[session_id] = updated_state
        
        # Build response
        response = _build_autonomous_response(
            updated_state,
            agent_decision
        )
        
        logger.info(
            f"Session {session_id}: Agent took {len(agent_decision.get('actions', []))} action(s), "
            f"stage={updated_state['journey_stage'].value}"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in autonomous interaction: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process interaction: {str(e)}"
        )


@router.get("/status/{session_id}", response_model=AutonomousResponse)
async def get_autonomous_status(session_id: str):
    """
    Get current status without any input.
    
    Useful for:
    - Periodic status checks
    - Reconnecting after disconnect
    - Debugging
    """
    
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    state = active_sessions[session_id]
    
    # Build response without agent decision
    response = _build_autonomous_response(state, {
        "actions": [],
        "response_message": "Status retrieved",
        "location_triggers": []
    })
    
    return response


@router.delete("/session/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def end_autonomous_session(session_id: str):
    """
    End an autonomous session.
    
    The agent will automatically complete the journey if needed.
    """
    
    if session_id in active_sessions:
        state = active_sessions[session_id]
        
        # Let agent handle departure if not already done
        if not state.get("visit_ended"):
            try:
                agent_decision = await autonomous_agent.process_input(
                    state,
                    user_message="Patient is leaving"
                )
                autonomous_agent.execute_actions(state, agent_decision.get("actions", []))
            except Exception as e:
                logger.warning(f"Could not complete journey on session end: {e}")
        
        logger.info(f"Ending autonomous session {session_id}")
        del active_sessions[session_id]
    
    return None


# ===== HELPER FUNCTIONS =====

def _build_autonomous_response(
    state: HospitalGuidanceState,
    agent_decision: Dict[str, Any]
) -> AutonomousResponse:
    """Build the unified response from state and agent decision"""
    
    # Extract message from agent decision or latest notification
    message = agent_decision.get("response_message", "")
    if not message and state.get("notifications"):
        latest_notif = state["notifications"][-1]
        message = latest_notif.get("message", "")
    
    # Convert actions to response format
    actions_taken = []
    for action in agent_decision.get("actions", []):
        actions_taken.append(AgentAction(
            action=action.get("action", "unknown"),
            params=action.get("params", {}),
            reasoning=agent_decision.get("reasoning")
        ))
    
    # Convert notifications
    notifications = []
    for notif in state.get("notifications", [])[-5:]:  # Last 5 notifications
        try:
            notifications.append(Notification(**notif))
        except Exception:
            pass
    
    return AutonomousResponse(
        session_id=state["session_id"],
        journey_stage=JourneyStageEnum(state["journey_stage"].value),
        actions_taken=actions_taken,
        message=message,
        current_location=state.get("current_location"),
        queue_position=state.get("queue_position"),
        estimated_wait_time=state.get("estimated_wait_time"),
        pending_tasks=state.get("pending_tasks", []),
        completed_tasks=state.get("completed_tasks", []),
        notifications=notifications,
        navigation_active=state.get("navigation_active", False),
        navigation_route=state.get("navigation_route"),
        destination=state.get("destination"),
        visit_started=state.get("visit_started", False),
        visit_ended=state.get("visit_ended", False),
        prescriptions_count=len(state.get("prescriptions", [])),
        tests_ordered_count=len(state.get("tests_ordered", [])),
        emergency_active=state.get("emergency_active", False),
        timestamp=datetime.now(),
        agent_reasoning=agent_decision.get("reasoning")
    )


# ===== ADDITIONAL UTILITY ENDPOINTS =====

@router.post("/emergency/{session_id}")
async def emergency_alert(session_id: str, description: str):
    """
    Emergency endpoint - bypasses agent and immediately handles emergency.
    
    Use this for critical situations where instant response is needed.
    """
    
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    state = active_sessions[session_id]
    
    # Force emergency action
    agent_decision = {
        "actions": [{
            "action": "handle_emergency",
            "params": {
                "emergency_type": "critical",
                "description": description
            }
        }],
        "response_message": "🚨 EMERGENCY - Help is on the way!",
        "reasoning": "Emergency button pressed"
    }
    
    # Execute immediately
    updated_state = autonomous_agent.execute_actions(state, agent_decision["actions"])
    active_sessions[session_id] = updated_state
    
    return _build_autonomous_response(updated_state, agent_decision)


@router.get("/sessions")
async def list_active_sessions():
    """
    List all active autonomous sessions.
    
    Useful for:
    - Hospital dashboard
    - Monitoring
    - Debugging
    """
    
    sessions = []
    for session_id, state in active_sessions.items():
        sessions.append({
            "session_id": session_id,
            "patient_id": state.get("patient_id"),
            "journey_stage": state.get("journey_stage", JourneyStage.ARRIVAL).value,
            "current_location": state.get("current_location", {}).get("name", "Unknown"),
            "started_at": state.get("started_at"),
            "last_updated": state.get("last_updated"),
            "emergency_active": state.get("emergency_active", False)
        })
    
    return {
        "total_sessions": len(sessions),
        "sessions": sessions
    }