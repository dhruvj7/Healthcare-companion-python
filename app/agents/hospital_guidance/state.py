from typing import TypedDict, List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

class JourneyStage(Enum):
    """Patient's current stage in hospital journey"""
    ARRIVAL = "arrival"
    CHECK_IN = "check_in"
    PRE_VISIT = "pre_visit"
    WAITING = "waiting"
    IN_VISIT = "in_visit"
    POST_VISIT = "post_visit"
    DEPARTURE = "departure"
    COMPLETED = "completed"

class LocationType(Enum):
    """Types of hospital locations"""
    ENTRANCE = "entrance"
    REGISTRATION = "registration"
    WAITING_ROOM = "waiting_room"
    EXAM_ROOM = "exam_room"
    LAB = "lab"
    PHARMACY = "pharmacy"
    CAFETERIA = "cafeteria"
    RESTROOM = "restroom"
    EXIT = "exit"

class PriorityLevel(Enum):
    """Task/notification priority"""
    CRITICAL = "critical"      # Emergency
    HIGH = "high"             # Important, time-sensitive
    MEDIUM = "medium"         # Should be done soon
    LOW = "low"               # Nice to have
class AppointmentStatus(Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class HospitalGuidanceState(TypedDict):
    # ===== SESSION INFO =====
    session_id: str
    patient_id: str
    hospital_id: str
    journey_stage: JourneyStage
    started_at: Optional[datetime]
    
    # ===== APPOINTMENT INFO =====
    appointment_id: str
    doctor_name: str
    appointment_time: datetime
    department: str
    reason_for_visit: str
    appointment_status: Optional[str]
    
    # ===== LOCATION & NAVIGATION =====
    current_location: Optional[Dict[str, Any]]  # {building, floor, room, coordinates}
    destination: Optional[Dict[str, Any]]
    navigation_active: bool
    navigation_route: Optional[List[Dict[str, Any]]]
    
    # ===== CHECK-IN STATUS =====
    check_in_completed: bool
    insurance_verified: bool
    forms_completed: bool
    copay_paid: bool

    # ===== INSURANCE DETAILS =====
    insurance_details: Optional[Dict[str, Any]]  # Validated insurance information
    insurance_validation_errors: Optional[List[Dict[str, str]]]  # Validation errors if any
    
    # ===== QUEUE MANAGEMENT =====
    queue_position: Optional[int]
    estimated_wait_time: Optional[int]  # minutes
    last_wait_update: Optional[datetime]
    
    # ===== VISIT INFORMATION =====
    visit_started: bool
    visit_ended: bool
    visit_summary: Optional[str]
    diagnosis: Optional[str]
    prescriptions: Optional[List[Dict[str, Any]]]
    tests_ordered: Optional[List[Dict[str, Any]]]
    follow_up_needed: bool
    
    # ===== FOLLOW-UP APPOINTMENT =====
    follow_up_appointment: Optional[Dict[str, Any]]
    # Structure:
    # {
    #     "appointment_id": str,
    #     "doctor_name": str,
    #     "appointment_time": datetime,
    #     "department": str,
    #     "reason": str,
    #     "type": str,  # "follow_up", "new", "urgent"
    #     "status": str,  # "scheduled", "confirmed"
    #     "confirmation_sent": bool,
    #     "reminder_sent": bool,
    #     "notes": str
    # }
        
    # ===== POST-VISIT TASKS =====
    pending_tasks: List[Dict[str, Any]]  # Lab work, pharmacy, billing, etc.
    completed_tasks: List[str]

    # NEW: Nearby amenities (separate from notifications)
    nearby_amenities: Optional[List[Dict[str, Any]]]
    amenities_last_updated: Optional[datetime]
    
    # ===== NOTIFICATIONS & ALERTS =====
    notifications: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]
    family_notified: bool
    
    # ===== PATIENT PREFERENCES =====
    language: str
    accessibility_needs: Optional[List[str]]
    notification_preferences: Dict[str, bool]  # SMS, email, push
    family_contacts: Optional[List[Dict[str, Any]]]
    
    # ===== INTERACTION HISTORY =====
    conversation_history: List[Dict[str, Any]]
    user_queries: List[str]
    agent_responses: List[str]
    
    # ===== EMERGENCY =====
    emergency_active: bool
    emergency_type: Optional[str]
    emergency_location: Optional[Dict[str, Any]]
    
    # ===== FEEDBACK =====
    feedback_collected: bool
    satisfaction_rating: Optional[int]
    
    # ===== METADATA =====
    last_updated: datetime
    context: Optional[Dict[str, Any]]  # Additional context