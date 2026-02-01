from pydantic import BaseModel, Field, validator
from typing import List, Optional

class SymptomRequest(BaseModel):
    symptoms: List[str] = Field(..., min_items=1, description="List of symptoms")
    duration: str = Field(..., description="How long symptoms have been present")
    age: Optional[int] = Field(None, ge=0, le=120)
    severity_self_assessment: Optional[int] = Field(None, ge=1, le=10)
    existing_conditions: Optional[List[str]] = Field(default=[])
    current_medications: Optional[List[str]] = Field(default=[])
    allergies: Optional[List[str]] = Field(default=[])
    
    @validator('symptoms')
    def validate_symptoms(cls, v):
        if not v or all(not s.strip() for s in v):
            raise ValueError("At least one symptom must be provided")
        return [s.strip() for s in v if s.strip()]
    
    class Config:
        json_schema_extra = {
            "example": {
                "symptoms": ["fever", "cough", "fatigue"],
                "duration": "3 days",
                "age": 35,
                "severity_self_assessment": 6,
                "existing_conditions": ["asthma"],
                "current_medications": ["albuterol"],
                "allergies": ["penicillin"]
            }
        }