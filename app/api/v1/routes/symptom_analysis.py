from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
import logging
import uuid

from app.models.request_models import SymptomRequest
from app.models.response_models import SymptomAnalysisResponse
from app.agents.symptom_analysis.agent import symptom_agent
from app.agents.doctor_finder.agent import doctor_agent

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze-symptoms", response_model=SymptomAnalysisResponse)
async def analyze_symptoms(request: SymptomRequest):
    try:
        conversation_id = str(uuid.uuid4())
        logger.info(f"Processing symptom analysis: {conversation_id}")

        # Initial shared state
        state = {
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

        # STEP 1: Symptom analysis agent
        state = symptom_agent.invoke(state)

        # STEP 2: Doctor matching agent (ALWAYS)
        state = doctor_agent.invoke(state)

        logger.info(
            f"Journey complete: {conversation_id} | "
            f"Severity={state.get('severity_classification')} | "
            f"Doctors={len(state.get('matched_doctors', []))}"
        )

        return SymptomAnalysisResponse(
            # Classification
            severity=state["severity_classification"],
            is_emergency=state.get("is_emergency", False),
            requires_doctor=state.get("requires_doctor", False),
            urgency_level=state.get("urgency_level", "routine"),
            confidence_score=state.get("confidence_score"),

            # Analysis
            primary_analysis=state.get("primary_analysis"),
            differential_diagnosis=state.get("differential_diagnosis"),
            reasoning=state.get("reasoning"),
            red_flags=state.get("red_flags"),

            # Recommendations
            immediate_actions=state.get("immediate_actions", []),
            home_care_advice=state.get("home_care_advice"),
            when_to_seek_help=state.get("when_to_seek_help"),
            preparation_for_doctor=state.get("preparation_for_doctor"),

            # Doctor matching (NEW)
            matched_doctors=state.get("matched_doctors", []),

            # Metadata
            conversation_id=state["conversation_id"],
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        logger.error(f"Error analyzing symptoms: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
