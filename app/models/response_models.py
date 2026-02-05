# app/models/response_models.py

from pydantic import BaseModel
from typing import List, Optional
from pydantic import ConfigDict

class SymptomAnalysisResponse(BaseModel):
    # Classification
    severity: str
    is_emergency: bool
    requires_doctor: bool
    urgency_level: str
    confidence_score: Optional[float] = None

    # Analysis
    primary_analysis: Optional[str] = None
    differential_diagnosis: Optional[List[str]] = None
    reasoning: Optional[str] = None
    red_flags: Optional[List[str]] = None

    # Recommendations
    immediate_actions: List[str]
    home_care_advice: Optional[List[str]] = None
    when_to_seek_help: Optional[List[str]] = None
    preparation_for_doctor: Optional[List[str]] = None

    # Care Coordination
    suggested_specialties: Optional[List[str]] = None
    matched_doctors: Optional[List[dict]] = None
    matched_hospitals: Optional[List[dict]] = None

    # Metadata
    conversation_id: str
    timestamp: str

    # Disclaimer
    disclaimer: str = (
        "⚠️ MEDICAL DISCLAIMER: This assessment is not a substitute for professional "
        "medical advice, diagnosis, or treatment. Always seek the advice of your "
        "physician or other qualified health provider with any questions you may have "
        "regarding a medical condition. In case of emergency, call 911/108 immediately."
    )

    # ✅ Pydantic v2 config
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "severity": "consult_doctor",
                "is_emergency": False,
                "requires_doctor": True,
                "urgency_level": "within_week",
                "confidence_score": 0.82,
                "primary_analysis": "Likely viral infection with respiratory symptoms",
                "differential_diagnosis": ["Upper respiratory infection", "Bronchitis"],
                "immediate_actions": ["Rest", "Hydration"],
                "suggested_specialties": ["General Medicine"],
                "matched_doctors": [
                    {
                        "name": "Dr. A. Sharma",
                        "hospital": "CarePlus Clinic"
                    }
                ],
                "conversation_id": "uuid",
                "timestamp": "2026-02-03T11:53:53"
            }
        }
    )
