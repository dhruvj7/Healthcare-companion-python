from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from enum import Enum

if TYPE_CHECKING:
    from typing import ForwardRef

# ===== ENUMS =====

class JourneyStageEnum(str, Enum):
    ARRIVAL = "arrival"
    CHECK_IN = "check_in"
    PRE_VISIT = "pre_visit"
    WAITING = "waiting"
    IN_VISIT = "in_visit"
    POST_VISIT = "post_visit"
    DEPARTURE = "departure"
    COMPLETED = "completed"

class IntentType(str, Enum):
    NAVIGATE = "navigate"
    CHECK_IN = "check_in"
    CHECK_WAIT = "check_wait"
    FIND_AMENITIES = "find_amenities"
    ASK_QUESTION = "ask_question"
    EXPLAIN_TERM = "explain_term"
    REPORT_SYMPTOMS = "report_symptoms"
    EMERGENCY = "emergency"
    PRESCRIPTION = "prescription"
    LAB_WORK = "lab_work"
    FOLLOW_UP = "follow_up"
    PAYMENT = "payment"
    DEPARTURE = "departure"
    GENERAL = "general"

class PharmacyChoice(str, Enum):
    HOSPITAL = "hospital"
    EXTERNAL = "external"

# ===== REQUEST MODELS =====

class InitializeJourneyRequest(BaseModel):
    """Initialize a new hospital journey"""
    patient_id: str = Field(..., description="Unique patient identifier")
    appointment_id: str = Field(..., description="Appointment ID")
    doctor_name: str = Field(..., description="Doctor's name")
    appointment_time: datetime = Field(..., description="Scheduled appointment time")
    department: str = Field(default="General", description="Hospital department")
    reason_for_visit: str = Field(..., description="Reason for visit")
    hospital_id: str = Field(default="hospital_001", description="Hospital identifier")
    
    # Optional patient preferences
    language: str = Field(default="en", description="Preferred language")
    accessibility_needs: Optional[List[str]] = Field(default=None, description="Accessibility requirements")
    family_contacts: Optional[List[Dict[str, Any]]] = Field(default=None, description="Emergency contacts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "patient_id": "P123456",
                "appointment_id": "APT789",
                "doctor_name": "Dr. Sarah Smith",
                "appointment_time": "2026-02-05T14:00:00",
                "department": "Cardiology",
                "reason_for_visit": "Follow-up for chest pain",
                "language": "en",
                "accessibility_needs": ["wheelchair"],
                "family_contacts": [
                    {
                        "name": "John Doe",
                        "relationship": "spouse",
                        "phone": "+1234567890",
                        "notify_by": ["sms", "call"]
                    }
                ]
            }
        }

class UserInteractionRequest(BaseModel):
    """User interaction with the agent"""
    session_id: str = Field(..., description="Active session ID")
    message: str = Field(..., description="User's message/query")
    intent: Optional[IntentType] = Field(default=None, description="Detected or specified intent")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "message": "Where is the cafeteria?",
                "intent": "find_amenities",
                "context": {}
            }
        }

class NavigationRequest(BaseModel):
    """Request for navigation assistance"""
    session_id: str = Field(..., description="Active session ID")
    destination_query: str = Field(..., description="Where the patient wants to go")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "destination_query": "Dr. Smith's office"
            }
        }

class LocationUpdateRequest(BaseModel):
    """Update patient's current location"""
    session_id: str = Field(..., description="Active session ID")
    location: Dict[str, Any] = Field(..., description="New location coordinates/info")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "location": {
                    "building": "A",
                    "floor": "2",
                    "room": "waiting_room_2a",
                    "coordinates": {"x": 10, "y": 20}
                }
            }
        }

class CheckInRequest(BaseModel):
    """Complete check-in process"""
    session_id: str = Field(..., description="Active session ID")
    insurance_card_image: Optional[str] = Field(default=None, description="Base64 encoded insurance card")
    medical_history_updates: Optional[Dict[str, Any]] = Field(default=None, description="Medical history changes")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "medical_history_updates": {
                    "new_medications": ["Aspirin 81mg"],
                    "new_allergies": []
                }
            }
        }

class InsuranceValidationRequest(BaseModel):
    """Validate insurance details"""
    provider_name: str = Field(..., description="Insurance provider name", min_length=2)
    policy_number: str = Field(..., description="Policy/member ID number", min_length=5)
    group_number: Optional[str] = Field(default=None, description="Group number if applicable")
    policy_holder_name: str = Field(..., description="Name of policy holder", min_length=2)
    policy_holder_dob: str = Field(..., description="Policy holder date of birth (YYYY-MM-DD)")
    relationship_to_patient: str = Field(..., description="Relationship to patient (self, spouse, parent, child)")
    effective_date: str = Field(..., description="Policy effective date (YYYY-MM-DD)")
    expiration_date: Optional[str] = Field(default=None, description="Policy expiration date (YYYY-MM-DD)")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_name": "Blue Cross Blue Shield",
                "policy_number": "ABC123456789",
                "group_number": "GRP001",
                "policy_holder_name": "John Doe",
                "policy_holder_dob": "1985-05-15",
                "relationship_to_patient": "self",
                "effective_date": "2025-01-01",
                "expiration_date": "2026-12-31"
            }
        }

class InsuranceValidationResponse(BaseModel):
    """Response for insurance validation"""
    session_id: str
    is_valid: bool
    validation_errors: List[Dict[str, str]] = []
    insurance_verified: bool = False
    message: str
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "is_valid": True,
                "validation_errors": [],
                "insurance_verified": True,
                "message": "Insurance details validated successfully",
                "timestamp": "2026-02-05T14:30:00"
            }
        }

class PrescriptionRequest(BaseModel):
    """Record or route prescription"""
    session_id: str = Field(..., description="Active session ID")
    action: str = Field(..., description="Action: 'record' or 'route'")
    
    # For recording
    medication: Optional[str] = Field(default=None)
    dosage: Optional[str] = Field(default=None)
    frequency: Optional[str] = Field(default=None)
    instructions: Optional[str] = Field(default=None)
    
    # For routing
    pharmacy_choice: Optional[PharmacyChoice] = Field(default=None)
    pharmacy_name: Optional[str] = Field(default=None)
    pharmacy_address: Optional[str] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "action": "record",
                "medication": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once daily",
                "instructions": "Take in the morning with food"
            }
        }

class LabWorkRequest(BaseModel):
    """Schedule or record lab work"""
    session_id: str = Field(..., description="Active session ID")
    action: str = Field(..., description="Action: 'record' or 'schedule'")
    
    # For recording
    test_name: Optional[str] = Field(default=None)
    test_type: Optional[str] = Field(default=None, description="lab, imaging, etc.")
    urgency: Optional[str] = Field(default="routine", description="routine, urgent, stat")
    test_instructions: Optional[str] = Field(default=None)
    
    # For scheduling
    schedule_now: Optional[bool] = Field(default=True)
    preferred_time: Optional[datetime] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "action": "schedule",
                "schedule_now": True
            }
        }

class FollowUpRequest(BaseModel):
    """Schedule follow-up appointment"""
    session_id: str = Field(..., description="Active session ID")
    preferred_date: datetime = Field(..., description="Preferred follow-up date")
    preferred_time: Optional[str] = Field(default=None, description="morning, afternoon, evening")
    notes: Optional[str] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "preferred_date": "2026-02-19T10:00:00",
                "preferred_time": "morning"
            }
        }

class EmergencyRequest(BaseModel):
    """Report emergency"""
    session_id: str = Field(..., description="Active session ID")
    emergency_type: Optional[str] = Field(default=None, description="Type of emergency if known")
    description: str = Field(..., description="What's happening")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "description": "Patient experiencing severe chest pain and shortness of breath"
            }
        }

class FeedbackRequest(BaseModel):
    """Submit feedback"""
    session_id: str = Field(..., description="Active session ID")
    rating: int = Field(..., ge=1, le=5, description="Overall rating 1-5")
    categories: Optional[Dict[str, int]] = Field(default=None, description="Category-specific ratings")
    comments: Optional[str] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "rating": 5,
                "categories": {
                    "navigation": 5,
                    "wait_time_communication": 4,
                    "staff_interaction": 5
                },
                "comments": "Very helpful guidance throughout my visit!"
            }
        }

# ===== RESPONSE MODELS =====

class LocationInfo(BaseModel):
    """Location information"""
    building: str
    building_name: Optional[str] = None
    floor: str
    room: Optional[str] = None
    name: str
    coordinates: Optional[Dict[str, float]] = None

class NavigationStep(BaseModel):
    """Single navigation step"""
    instruction: str
    distance: Optional[float] = None
    type: str  # walk, elevator, outdoor_walk, arrival

class NavigationRoute(BaseModel):
    """Complete navigation route"""
    distance: float
    estimated_time: int  # seconds
    steps: List[NavigationStep]
    accessible: bool

class Task(BaseModel):
    """Pending task"""
    task_id: str
    type: str  # prescription, lab, appointment, billing
    priority: str
    title: str
    description: str
    status: str  # pending, in_progress, completed
    options: Optional[List[Dict[str, Any]]] = None
    location: Optional[LocationInfo] = None

class Notification(BaseModel):
    """Notification/alert"""
    id: Optional[str] = None
    type: str  # info, warning, success, error, emergency
    priority: Optional[str] = None
    title: str
    message: str
    timestamp: datetime
    action: Optional[str] = None
    route: Optional[NavigationRoute] = None
    tasks: Optional[List[Task]] = None

class QueueStatus(BaseModel):
    """Queue status information"""
    queue_position: Optional[int] = None
    estimated_wait_time: Optional[int] = None  # minutes
    patients_ahead: Optional[int] = None
    last_updated: datetime

class Prescription(BaseModel):
    """Prescription information"""
    medication: str
    dosage: str
    frequency: str
    instructions: str
    prescribed_at: datetime
    prescribed_by: str

class TestOrder(BaseModel):
    """Lab/imaging test order"""
    test_name: str
    test_type: str
    urgency: str
    instructions: str
    ordered_at: datetime
    ordered_by: str
    completed: bool

class JourneyResponse(BaseModel):
    """Main response for journey operations"""
    session_id: str
    journey_stage: JourneyStageEnum
    patient_id: str
    
    # Current status
    current_location: Optional[LocationInfo] = None
    destination: Optional[LocationInfo] = None
    navigation_active: bool = False
    navigation_route: Optional[List[NavigationStep]] = None

    # NEW: Nearby amenities (separate from notifications)
    nearby_amenities: Optional[List['Amenity']] = None
    amenities_last_updated: Optional[datetime] = None
    
    # Check-in status
    check_in_completed: bool = False
    insurance_verified: bool = False
    forms_completed: bool = False
    copay_paid: bool = False
    
    # Queue information
    queue_status: Optional[QueueStatus] = None
    
    # Visit information
    visit_started: bool = False
    visit_ended: bool = False
    visit_summary: Optional[str] = None
    diagnosis: Optional[str] = None
    prescriptions: Optional[List[Prescription]] = None
    tests_ordered: Optional[List[TestOrder]] = None
    
    # Tasks
    pending_tasks: List[Task] = []
    completed_tasks: List[str] = []

    # Current visit appointment
    current_appointment: Optional['AppointmentInfo'] = None

    # Follow-up appointment (separate from notifications!)
    follow_up_appointment: Optional['AppointmentInfo'] = None
    
    # Communications
    notifications: List[Notification] = []
    
    # Emergency
    emergency_active: bool = False
    
    # Metadata
    last_updated: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "journey_stage": "waiting",
                "patient_id": "P123456",
                "current_location": {
                    "building": "A",
                    "floor": "2",
                    "name": "Waiting Room 2A"
                },
                "check_in_completed": True,
                "queue_status": {
                    "queue_position": 3,
                    "estimated_wait_time": 25,
                    "patients_ahead": 2,
                    "last_updated": "2026-02-05T14:15:00"
                },
                "notifications": [
                    {
                        "type": "info",
                        "title": "Wait Time Update",
                        "message": "You're 3rd in line, estimated wait: 25 minutes",
                        "timestamp": "2026-02-05T14:15:00"
                    }
                ],
                "last_updated": "2026-02-05T14:15:00"
            }
        }

class ConversationResponse(BaseModel):
    """Response to user interaction"""
    session_id: str
    response_message: str
    intent_detected: Optional[IntentType] = None
    journey_updated: bool = False
    journey_stage: JourneyStageEnum
    notifications: List[Notification] = []
    suggested_actions: Optional[List[Dict[str, str]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "response_message": "The cafeteria is on the 1st floor. It's about a 5-minute walk from your current location. Would you like me to guide you there?",
                "intent_detected": "find_amenities",
                "journey_updated": False,
                "journey_stage": "waiting",
                "notifications": [],
                "suggested_actions": [
                    {
                        "action": "navigate_to_cafeteria",
                        "label": "Yes, guide me there"
                    },
                    {
                        "action": "dismiss",
                        "label": "No, thanks"
                    }
                ]
            }
        }

class EmergencyResponse(BaseModel):
    """Emergency activation response"""
    session_id: str
    emergency_active: bool
    emergency_type: str
    message: str
    instructions: List[str]
    staff_alerted: bool
    family_notified: bool
    location: LocationInfo
    timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "emergency_active": True,
                "emergency_type": "cardiac",
                "message": "🚨 CARDIAC EMERGENCY - Medical staff alerted. Stay where you are. Help is on the way.",
                "instructions": [
                    "Stay as still as possible",
                    "Loosen tight clothing",
                    "Medical team arriving in less than 2 minutes"
                ],
                "staff_alerted": True,
                "family_notified": True,
                "location": {
                    "building": "A",
                    "floor": "2",
                    "name": "Waiting Room 2A"
                },
                "timestamp": "2026-02-05T14:30:00"
            }
        }

class SessionInfo(BaseModel):
    """Session information"""
    session_id: str
    patient_id: str
    created_at: datetime
    last_activity: datetime
    journey_stage: JourneyStageEnum
    active: bool

class Amenity(BaseModel):
    """Nearby amenity information"""
    id: str
    name: str
    type: str  # restroom, food, pharmacy, etc.
    distance: float  # in feet
    walking_time: int  # in seconds
    direction: str  # north, south, east, west
    
    # Optional fields
    wheelchair_accessible: bool = True
    hours: Optional[str] = None
    currently_open: Optional[bool] = None
    available: bool = True
    
    # Location details
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "amenity_restroom_2a",
                "name": "Restroom 2A",
                "type": "restroom",
                "distance": 10,
                "walking_time": 3,
                "direction": "east",
                "wheelchair_accessible": True,
                "hours": "24/7",
                "currently_open": True,
                "available": True,
                "building": "A",
                "floor": "2",
                "room": "restroom_2a"
            }
        }

class AppointmentInfo(BaseModel):
    """Detailed appointment information"""
    appointment_id: str
    doctor_name: str
    appointment_time: datetime
    department: str
    reason: str
    
    # Appointment metadata
    type: str = "follow_up"  # follow_up, new, urgent, routine
    status: str = "scheduled"  # scheduled, confirmed, completed, cancelled
    
    # Location details
    building: Optional[str] = None
    floor: Optional[str] = None
    room: Optional[str] = None
    
    # Preparation
    preparation_required: Optional[List[str]] = None  # "Fasting", "Bring medications"
    estimated_duration: Optional[int] = None  # minutes
    
    # Confirmations
    confirmation_sent: bool = False
    reminder_sent: bool = False
    
    # Additional info
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "appointment_id": "APT1001",
                "doctor_name": "Dr. Sarah Smith",
                "appointment_time": "2026-02-19T10:00:00",
                "department": "Cardiology",
                "reason": "Follow-up for chest pain management",
                "type": "follow_up",
                "status": "scheduled",
                "building": "A",
                "floor": "3",
                "room": "305",
                "preparation_required": ["Bring medication list", "Fasting not required"],
                "estimated_duration": 30,
                "confirmation_sent": True,
                "reminder_sent": False,
                "notes": "Bring previous test results",
                "created_at": "2026-02-05T10:30:00"
            }
        }


class JourneyResponse(BaseModel):
    """Main response for journey operations"""
    session_id: str
    journey_stage: JourneyStageEnum
    patient_id: str
    
    # Current status
    current_location: Optional[LocationInfo] = None
    destination: Optional[LocationInfo] = None
    navigation_active: bool = False
    navigation_route: Optional[List[NavigationStep]] = None

    # NEW: Nearby amenities (separate from notifications)
    nearby_amenities: Optional[List[Amenity]] = None
    amenities_last_updated: Optional[datetime] = None
    
    # Check-in status
    check_in_completed: bool = False
    insurance_verified: bool = False
    forms_completed: bool = False
    copay_paid: bool = False
    
    # Queue information
    queue_status: Optional[QueueStatus] = None
    
    # Visit information
    visit_started: bool = False
    visit_ended: bool = False
    visit_summary: Optional[str] = None
    diagnosis: Optional[str] = None
    prescriptions: Optional[List[Prescription]] = None
    tests_ordered: Optional[List[TestOrder]] = None
    
    # Tasks
    pending_tasks: List[Task] = []
    completed_tasks: List[str] = []

    # Current visit appointment
    current_appointment: Optional[AppointmentInfo] = None
    
    # Follow-up appointment (separate from notifications!)
    follow_up_appointment: Optional[AppointmentInfo] = None
    
    # Communications
    notifications: List[Notification] = []
    
    # Emergency
    emergency_active: bool = False
    
    # Metadata
    last_updated: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "journey_stage": "waiting",
                "patient_id": "P123456",
                "current_location": {
                    "building": "A",
                    "floor": "2",
                    "name": "Waiting Room 2A"
                },
                "check_in_completed": True,
                "queue_status": {
                    "queue_position": 3,
                    "estimated_wait_time": 25,
                    "patients_ahead": 2,
                    "last_updated": "2026-02-05T14:15:00"
                },
                "notifications": [
                    {
                        "type": "info",
                        "title": "Wait Time Update",
                        "message": "You're 3rd in line, estimated wait: 25 minutes",
                        "timestamp": "2026-02-05T14:15:00"
                    }
                ],
                "last_updated": "2026-02-05T14:15:00"
            }
        }
