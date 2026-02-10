from typing import Dict, TypedDict, List, Optional
from enum import Enum

class Severity(Enum):
    HOME_CARE = "home_care"
    CONSULT_DOCTOR = "consult_doctor"
    URGENT_CARE = "urgent_care"
    EMERGENCY = "emergency"

class AgeGroup(Enum):
    INFANT = "infant"
    CHILD = "child"
    TEEN = "teen"
    ADULT = "adult"
    SENIOR = "senior"

class SymptomAnalysisState(TypedDict):
    # Input
    symptoms: List[str]
    duration: str
    severity_self_assessment: Optional[int]
    age: Optional[int]
    age_group: Optional[AgeGroup]
    existing_conditions: Optional[List[str]]
    current_medications: Optional[List[str]]
    allergies: Optional[List[str]]
    
    # Extracted
    symptom_keywords: Optional[List[str]]
    red_flags: Optional[List[str]]
    
    # Analysis
    primary_analysis: Optional[str]
    severity_classification: Optional[Severity]
    confidence_score: Optional[float]
    differential_diagnosis: Optional[List[str]]
    reasoning: Optional[str]
    
    # Recommendations
    immediate_actions: Optional[List[str]]
    home_care_advice: Optional[List[str]]
    when_to_seek_help: Optional[List[str]]
    preparation_for_doctor: Optional[List[str]]
    
    # Output
    requires_doctor: bool
    is_emergency: bool
    urgency_level: Optional[str]

        # Care Coordination (NEW)
    suggested_specialties: Optional[List[str]]
    matched_doctors: Optional[List[dict]]
    matched_hospitals: Optional[List[dict]]
    available_appointments: Optional[Dict[int, List[dict]]]

    
    # Metadata
    timestamp: Optional[str]
    conversation_id: Optional[str]