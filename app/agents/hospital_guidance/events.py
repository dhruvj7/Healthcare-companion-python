from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class EventType(str, Enum):
    LOCATION_UPDATED = "location_updated"
    ENTERED_HOSPITAL = "entered_hospital"
    REACHED_REGISTRATION = "reached_registration"
    REACHED_WAITING_ROOM = "reached_waiting_room"
    REACHED_EXAM_ROOM = "reached_exam_room"
    REACHED_PHARMACY = "reached_pharmacy"
    REACHED_LAB = "reached_lab"
    REACHED_EXIT = "reached_exit"

    APPOINTMENT_TIME_NEAR = "appointment_time_near"
    WAIT_TIME_ELAPSED = "wait_time_elapsed"
    REMINDER_DUE = "reminder_due"

    QUEUE_POSITION_CHANGED = "queue_position_changed"
    NEXT_IN_QUEUE = "next_in_queue"
    DOCTOR_READY = "doctor_ready"

    USER_MESSAGE = "user_message"
    BUTTON_CLICKED = "button_clicked"
    QR_CODE_SCANNED = "qr_code_scanned"

    CHECK_IN_COMPLETED = "check_in_completed"
    VISIT_STARTED = "visit_started"
    VISIT_ENDED = "visit_ended"
    PRESCRIPTION_READY = "prescription_ready"
    LAB_RESULTS_READY = "lab_results_ready"

    EMERGENCY_DETECTED = "emergency_detected"
    VITALS_ABNORMAL = "vitals_abnormal"


class HospitalEvent(BaseModel):
    event_type: EventType
    event_data: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = "frontend"
    priority: EventPriority = "normal"
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "location_updated",
                "event_data": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "detected_area": "registration",
                    "accuracy": 5.0
                },
                "timestamp": "2026-02-05T10:30:00",
                "source": "frontend",
                "priority": "normal"
            }
        }

class EventPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class LocationArea(Enum):
    """Predefined hospital areas"""
    OUTSIDE = "outside"
    PARKING = "parking"
    ENTRANCE = "entrance"
    REGISTRATION = "registration"
    WAITING_ROOM = "waiting_room"
    EXAM_ROOM = "exam_room"
    LAB = "lab"
    PHARMACY = "pharmacy"
    CAFETERIA = "cafeteria"
    RESTROOM = "restroom"
    EXIT = "exit"
    UNKNOWN = "unknown"


def detect_area_from_coordinates(latitude: float, longitude: float) -> LocationArea:
    """
    Detect which area of hospital based on GPS coordinates
    In production, this would use geofencing or beacon triangulation
    """
    
    # Example: Hospital coordinates
    HOSPITAL_LAT = 40.7128
    HOSPITAL_LNG = -74.0060
    
    # Calculate distance from hospital center
    import math
    distance = math.sqrt(
        (latitude - HOSPITAL_LAT)**2 + 
        (longitude - HOSPITAL_LNG)**2
    )
    
    # Simple distance-based detection (in production, use geofences)
    if distance > 0.001:  # ~111 meters
        return LocationArea.OUTSIDE
    elif distance > 0.0005:
        return LocationArea.PARKING
    elif distance > 0.0002:
        return LocationArea.ENTRANCE
    else:
        # Would use more precise indoor positioning
        return LocationArea.UNKNOWN


def detect_area_from_beacon(beacon_id: str) -> LocationArea:
    """Detect area from iBeacon/BLE beacon"""
    
    beacon_map = {
        "beacon_entrance": LocationArea.ENTRANCE,
        "beacon_registration": LocationArea.REGISTRATION,
        "beacon_waiting_2a": LocationArea.WAITING_ROOM,
        "beacon_exam_201": LocationArea.EXAM_ROOM,
        "beacon_lab": LocationArea.LAB,
        "beacon_pharmacy": LocationArea.PHARMACY,
        "beacon_exit": LocationArea.EXIT
    }
    
    return beacon_map.get(beacon_id, LocationArea.UNKNOWN)