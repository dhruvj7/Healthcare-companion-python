# app/models/response_models.py
from pydantic import BaseModel
from typing import List, Optional

class SymptomAnalysisResponse(BaseModel):
    # Classification
    severity: str
    is_emergency: bool
    requires_doctor: bool
    urgency_level: str
    confidence_score: Optional[float]
    
    # Analysis
    primary_analysis: Optional[str]
    differential_diagnosis: Optional[List[str]]
    reasoning: Optional[str]
    red_flags: Optional[List[str]]
    
    # Recommendations
    immediate_actions: List[str]
    home_care_advice: Optional[List[str]]
    when_to_seek_help: Optional[List[str]]
    preparation_for_doctor: Optional[List[str]]
    
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
    
    class Config:
        # Convert Enum to string value automatically
        use_enum_values = True