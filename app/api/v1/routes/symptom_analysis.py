from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
import logging
import uuid

from app.models.request_models import SymptomRequest
from app.models.response_models import SymptomAnalysisResponse
from app.agents.symptom_analysis.agent import symptom_agent

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze-symptoms", response_model=SymptomAnalysisResponse)
async def analyze_symptoms(request: SymptomRequest):
    """
    Analyze symptoms and provide triage recommendations
    """
    try:
        conversation_id = str(uuid.uuid4())
        
        logger.info(f"Processing symptom analysis: {conversation_id}")
        
        initial_state = {
            "symptoms": request.symptoms,
            "duration": request.duration,
            "age": request.age,
            "severity_self_assessment": request.severity_self_assessment,
            "existing_conditions": request.existing_conditions or [],
            "current_medications": request.current_medications or [],
            "allergies": request.allergies or [],
            "requires_doctor": False,
            "is_emergency": False,
            "conversation_id": conversation_id
        }
        
        result = symptom_agent.invoke(initial_state)
        
        logger.info(f"Analysis complete: {conversation_id} - Severity: {result['severity_classification']}")
        
        return SymptomAnalysisResponse(
        # Classification
        severity=result["severity_classification"],
        is_emergency=result.get("is_emergency", False),
        requires_doctor=result.get("requires_doctor", False),
        urgency_level=result.get("urgency_level", "routine"),
        confidence_score=result.get("confidence_score"),

        # Analysis
        primary_analysis=result.get("primary_analysis"),
        differential_diagnosis=result.get("differential_diagnosis"),
        reasoning=result.get("reasoning"),
        red_flags=result.get("red_flags"),

        # Recommendations
        immediate_actions=result.get("immediate_actions", ["Monitor symptoms"]),
        home_care_advice=result.get("home_care_advice"),
        when_to_seek_help=result.get("when_to_seek_help"),
        preparation_for_doctor=result.get("preparation_for_doctor"),

        # Metadata
        conversation_id=result["conversation_id"],
        timestamp=datetime.now().isoformat(),
    )
        
    except Exception as e:
        logger.error(f"Error analyzing symptoms: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing symptoms: {str(e)}"
        )