# app/api/v1/routes/insurance.py

"""
Insurance Validation Router

Handles all insurance-related operations for the hospital guidance system.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict
from datetime import datetime
import logging

from app.models.hospital_models import (
    InsuranceValidationRequest,
    InsuranceValidationResponse
)
from app.agents.hospital_guidance.state import HospitalGuidanceState
from app.agents.hospital_guidance.nodes.insurance_validation import validate_insurance
from app.services.insurance_provider_detector import detect_provider, get_available_providers
from app.services.insurance_verifier import get_policy_details

logger = logging.getLogger(__name__)
router = APIRouter()

# Import active_sessions from hospital_guidance router
# In production, this should be in a shared session manager
active_sessions: Dict[str, HospitalGuidanceState] = {}


def set_active_sessions(sessions: Dict[str, HospitalGuidanceState]):
    """Set the active sessions reference from the main hospital guidance router"""
    global active_sessions
    active_sessions = sessions


def _get_session(session_id: str) -> HospitalGuidanceState:
    """Get session or raise 404"""
    if session_id not in active_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    return active_sessions[session_id]


@router.post("/validate/{session_id}", response_model=InsuranceValidationResponse)
async def validate_insurance_details(session_id: str, request: InsuranceValidationRequest):
    """
    Validate insurance details

    Performs comprehensive validation of insurance information including:
    - Provider name verification
    - Policy number format validation
    - Date validations (DOB, effective date, expiration date)
    - Relationship to patient validation
    - Policy active status check

    Returns detailed error messages for any validation failures.


    **State Management:**
    - On success: Saves insurance details to session state
    - On failure: Saves validation errors to session state

    **Example Request:**
    ```json
    {
      "provider_name": "Blue Cross Blue Shield",
      "policy_number": "ABC123456789",
      "group_number": "GRP001",
      "policy_holder_name": "John Doe",
      "policy_holder_dob": "1985-05-15",
      "relationship_to_patient": "self",
      "effective_date": "2025-01-01",
      "expiration_date": "2026-12-31"
    }
    ```

    **Example Success Response:**
    ```json
    {
      "session_id": "sess_abc123",
      "is_valid": true,
      "validation_errors": [],
      "insurance_verified": true,
      "message": "Insurance details validated successfully and saved to your session",
      "timestamp": "2026-02-05T14:30:00"
    }
    ```

    **Example Failure Response:**
    ```json
    {
      "session_id": "sess_abc123",
      "is_valid": false,
      "validation_errors": [
        {
          "field": "policy_number",
          "error": "Policy number must be at least 5 characters long",
          "received_value": "123"
        }
      ],
      "insurance_verified": false,
      "message": "Insurance validation failed with 1 error(s). Please review and correct the issues.",
      "timestamp": "2026-02-05T14:30:00"
    }
    ```
    """
    state = _get_session(session_id)

    try:
        logger.info(f"Validating insurance for session {session_id}")
        logger.info(f"Request data: provider={request.provider_name}, policy={request.policy_number}")

        # Convert request to dict
        insurance_data = {
            "provider_name": request.provider_name,
            "policy_number": request.policy_number,
            "group_number": request.group_number,
            "policy_holder_name": request.policy_holder_name,
            "policy_holder_dob": request.policy_holder_dob,
            "relationship_to_patient": request.relationship_to_patient,
            "effective_date": request.effective_date,
            "expiration_date": request.expiration_date
        }

        logger.debug(f"Converted insurance data: {insurance_data}")

        # Validate insurance
        result = validate_insurance(state, insurance_data)

        # Update session
        active_sessions[session_id] = result
        logger.info(f"Session {session_id} state updated")

        # Build response
        is_valid = result.get("insurance_verified", False)
        validation_errors = result.get("insurance_validation_errors", [])
        if validation_errors is None:
            validation_errors = []

        if is_valid:
            logger.info(f"✅ Insurance validation SUCCESSFUL for session {session_id}")
            message = "Insurance details validated successfully and saved to your session"
        else:
            error_count = len([e for e in validation_errors if e.get("severity") != "warning"])
            logger.warning(f"❌ Insurance validation FAILED for session {session_id} with {error_count} error(s)")
            message = f"Insurance validation failed with {error_count} error(s). Please review and correct the issues."

        response = InsuranceValidationResponse(
            session_id=session_id,
            is_valid=is_valid,
            validation_errors=validation_errors,
            insurance_verified=is_valid,
            message=message,
            timestamp=datetime.now()
        )

        logger.info(f"Returning response: is_valid={is_valid}, errors_count={len(validation_errors)}")
        return response

    except Exception as e:
        logger.error(f"Error validating insurance: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate insurance: {str(e)}"
        )


@router.get("/status/{session_id}")
async def get_insurance_status(session_id: str):
    """
    Get current insurance validation status

    Returns the insurance verification status and any stored insurance details
    for the given session.

    **Response:**
    ```json
    {
      "session_id": "sess_abc123",
      "insurance_verified": true,
      "has_insurance_details": true,
      "has_validation_errors": false,
      "insurance_details": {
        "provider_name": "Blue Cross Blue Shield",
        "policy_number": "ABC123456789",
        "validated_at": "2026-02-05T14:30:00"
      }
    }
    ```
    """
    state = _get_session(session_id)

    try:
        logger.info(f"Retrieving insurance status for session {session_id}")

        insurance_verified = state.get("insurance_verified", False)
        insurance_details = state.get("insurance_details")
        validation_errors = state.get("insurance_validation_errors")

        response = {
            "session_id": session_id,
            "insurance_verified": insurance_verified,
            "has_insurance_details": insurance_details is not None,
            "has_validation_errors": validation_errors is not None and len(validation_errors) > 0,
        }

        # Include insurance details if present (excluding sensitive data)
        if insurance_details:
            response["insurance_details"] = {
                "provider_name": insurance_details.get("provider_name"),
                "policy_holder_name": insurance_details.get("policy_holder_name"),
                "relationship_to_patient": insurance_details.get("relationship_to_patient"),
                "validated_at": insurance_details.get("validated_at"),
                "validated": insurance_details.get("validated")
            }

        # Include validation errors if present
        if validation_errors:
            response["validation_errors"] = validation_errors

        logger.info(f"Insurance status retrieved: verified={insurance_verified}")
        return response

    except Exception as e:
        logger.error(f"Error retrieving insurance status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve insurance status: {str(e)}"
        )


@router.delete("/clear/{session_id}")
async def clear_insurance_data(session_id: str):
    """
    Clear insurance data from session

    Removes insurance details and validation errors from the session state.
    Useful when patient wants to re-enter insurance information.

    **Response:**
    ```json
    {
      "status": "success",
      "message": "Insurance data cleared successfully",
      "session_id": "sess_abc123"
    }
    ```
    """
    state = _get_session(session_id)

    try:
        logger.info(f"Clearing insurance data for session {session_id}")

        # Clear insurance-related fields
        state["insurance_details"] = None
        state["insurance_validation_errors"] = None
        state["insurance_verified"] = False
        state["last_updated"] = datetime.now()

        # Update session
        active_sessions[session_id] = state

        logger.info(f"Insurance data cleared for session {session_id}")

        return {
            "status": "success",
            "message": "Insurance data cleared successfully",
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Error clearing insurance data: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear insurance data: {str(e)}"
        )


@router.post("/detect-provider")
async def detect_provider_endpoint(provider_name: str, use_llm: bool = True):
    """
    Detect insurance provider using LLM/rule-based matching

    This endpoint helps identify which insurance provider the user is referring to.
    Useful for testing provider detection before full validation.

    **Query Parameters:**
    - `provider_name`: The insurance provider name to detect
    - `use_llm`: Whether to use LLM for detection (default: true)

    **Example:**
    ```
    POST /api/v1/insurance/detect-provider?provider_name=Blue Cross&use_llm=true
    ```

    **Response:**
    ```json
    {
      "detected_provider": "blue_cross_blue_shield",
      "csv_filename": "blue_cross_blue_shield.csv",
      "confidence": 0.95,
      "reasoning": "User mentioned 'Blue Cross' which clearly refers to Blue Cross Blue Shield",
      "detection_method": "llm"
    }
    ```
    """
    try:
        logger.info(f"Provider detection request: '{provider_name}' (use_llm={use_llm})")

        result = detect_provider(provider_name, use_llm=use_llm)

        logger.info(f"Detection result: {result['detected_provider']} (confidence: {result['confidence']})")

        return result

    except Exception as e:
        logger.error(f"Error detecting provider: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect provider: {str(e)}"
        )


@router.get("/providers")
async def list_available_providers():
    """
    List all available insurance providers

    Returns a list of all insurance providers that have CSV data files available.

    **Response:**
    ```json
    {
      "providers": [
        {
          "canonical_name": "blue_cross_blue_shield",
          "display_name": "Blue Cross Blue Shield",
          "csv_filename": "blue_cross_blue_shield.csv"
        }
      ],
      "count": 4
    }
    ```
    """
    try:
        logger.info("Fetching list of available providers")

        providers = get_available_providers()

        logger.info(f"Found {len(providers)} available providers")

        return {
            "providers": providers,
            "count": len(providers)
        }

    except Exception as e:
        logger.error(f"Error listing providers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list providers: {str(e)}"
        )


@router.get("/policy/{provider_name}/{policy_number}")
async def lookup_policy(provider_name: str, policy_number: str):
    """
    Lookup policy details without full validation

    Retrieves policy information from the insurance provider's database
    without requiring all verification details.

    **Path Parameters:**
    - `provider_name`: Insurance provider name
    - `policy_number`: Policy number to lookup

    **Example:**
    ```
    GET /api/v1/insurance/policy/Blue Cross/ABC123456789
    ```

    **Response:**
    ```json
    {
      "policy_found": true,
      "policy_details": {
        "policy_number": "ABC123456789",
        "group_number": "GRP001",
        "policy_holder_name": "John Doe",
        "status": "active",
        "coverage_type": "PPO",
        "copay_amount": "45"
      }
    }
    ```
    """
    try:
        logger.info(f"Policy lookup: {policy_number} from {provider_name}")

        policy_details = get_policy_details(provider_name, policy_number)

        if policy_details:
            logger.info(f"Policy found: {policy_number}")
            return {
                "policy_found": True,
                "policy_details": policy_details
            }
        else:
            logger.warning(f"Policy not found: {policy_number}")
            return {
                "policy_found": False,
                "message": f"Policy {policy_number} not found for provider {provider_name}"
            }

    except Exception as e:
        logger.error(f"Error looking up policy: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to lookup policy: {str(e)}"
        )
