# app/agents/hospital_guidance/nodes/insurance_validation.py

from typing import Dict, Any, List
import logging
from datetime import datetime
import re

from app.agents.hospital_guidance.state import HospitalGuidanceState, PriorityLevel
from app.services.insurance_verifier import verify_insurance as verify_insurance_with_provider

logger = logging.getLogger(__name__)

# Valid insurance providers (can be expanded)
VALID_PROVIDERS = [
    "blue cross blue shield", "bcbs", "aetna", "cigna", "united healthcare",
    "humana", "kaiser permanente", "anthem", "wellpoint", "medicare", "medicaid",
    "uhc", "united", "kaiser", "carefirst", "highmark"
]

# Valid relationship types
VALID_RELATIONSHIPS = ["self", "spouse", "parent", "child", "domestic partner", "other"]


def validate_insurance(
    state: HospitalGuidanceState,
    insurance_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Comprehensive insurance validation with detailed error reporting

    Validates:
    - Provider name format and recognition
    - Policy number format
    - Date formats and validity
    - Relationship to patient
    - Policy active status
    """

    logger.info(f"Starting insurance validation for patient {state['patient_id']}")
    logger.info(f"Insurance data received: {insurance_data}")

    validation_errors: List[Dict[str, str]] = []
    is_valid = True

    # ===== 1. PROVIDER NAME VALIDATION =====
    provider_name = insurance_data.get("provider_name", "").strip()
    logger.debug(f"Validating provider name: '{provider_name}'")

    if not provider_name:
        error = {
            "field": "provider_name",
            "error": "Provider name is required",
            "received_value": provider_name
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    elif len(provider_name) < 2:
        error = {
            "field": "provider_name",
            "error": "Provider name must be at least 2 characters long",
            "received_value": provider_name
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    else:
        # Check if provider is recognized
        provider_lower = provider_name.lower()
        is_recognized = any(valid_provider in provider_lower for valid_provider in VALID_PROVIDERS)

        if not is_recognized:
            logger.warning(f"Unrecognized insurance provider: {provider_name}")
            # This is a warning, not a hard failure
            validation_errors.append({
                "field": "provider_name",
                "error": "Warning: Insurance provider not recognized. Please verify the name is correct.",
                "received_value": provider_name,
                "severity": "warning"
            })
        else:
            logger.info(f"Provider recognized: {provider_name}")

    # ===== 2. POLICY NUMBER VALIDATION =====
    policy_number = insurance_data.get("policy_number", "").strip()
    logger.debug(f"Validating policy number: '{policy_number}'")

    if not policy_number:
        error = {
            "field": "policy_number",
            "error": "Policy number is required",
            "received_value": policy_number
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    elif len(policy_number) < 5:
        error = {
            "field": "policy_number",
            "error": "Policy number must be at least 5 characters long",
            "received_value": policy_number
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    else:
        # Check for valid characters (alphanumeric and hyphens)
        if not re.match(r'^[A-Za-z0-9\-]+$', policy_number):
            error = {
                "field": "policy_number",
                "error": "Policy number can only contain letters, numbers, and hyphens",
                "received_value": policy_number
            }
            validation_errors.append(error)
            is_valid = False
            logger.warning(f"Validation error: {error}")
        else:
            logger.info(f"Policy number format valid: {policy_number}")

    # ===== 3. GROUP NUMBER VALIDATION (OPTIONAL) =====
    group_number = insurance_data.get("group_number", "")
    if group_number:
        logger.debug(f"Validating group number: '{group_number}'")
        if not re.match(r'^[A-Za-z0-9\-]+$', group_number):
            error = {
                "field": "group_number",
                "error": "Group number can only contain letters, numbers, and hyphens",
                "received_value": group_number
            }
            validation_errors.append(error)
            is_valid = False
            logger.warning(f"Validation error: {error}")

    # ===== 4. POLICY HOLDER NAME VALIDATION =====
    policy_holder_name = insurance_data.get("policy_holder_name", "").strip()
    logger.debug(f"Validating policy holder name: '{policy_holder_name}'")

    if not policy_holder_name:
        error = {
            "field": "policy_holder_name",
            "error": "Policy holder name is required",
            "received_value": policy_holder_name
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    elif len(policy_holder_name) < 2:
        error = {
            "field": "policy_holder_name",
            "error": "Policy holder name must be at least 2 characters long",
            "received_value": policy_holder_name
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    else:
        logger.info(f"Policy holder name valid: {policy_holder_name}")

    # ===== 5. POLICY HOLDER DOB VALIDATION =====
    policy_holder_dob = insurance_data.get("policy_holder_dob", "")
    logger.debug(f"Validating policy holder DOB: '{policy_holder_dob}'")

    if not policy_holder_dob:
        error = {
            "field": "policy_holder_dob",
            "error": "Policy holder date of birth is required",
            "received_value": policy_holder_dob
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    else:
        try:
            dob_date = datetime.strptime(policy_holder_dob, "%Y-%m-%d")

            # Check if date is in the future
            if dob_date > datetime.now():
                error = {
                    "field": "policy_holder_dob",
                    "error": "Date of birth cannot be in the future",
                    "received_value": policy_holder_dob
                }
                validation_errors.append(error)
                is_valid = False
                logger.warning(f"Validation error: {error}")

            # Check if date is reasonable (not more than 120 years ago)
            age_years = (datetime.now() - dob_date).days / 365.25
            if age_years > 120:
                error = {
                    "field": "policy_holder_dob",
                    "error": "Date of birth is too far in the past (max age: 120 years)",
                    "received_value": policy_holder_dob
                }
                validation_errors.append(error)
                is_valid = False
                logger.warning(f"Validation error: {error}")
            else:
                logger.info(f"Policy holder DOB valid: {policy_holder_dob}")

        except ValueError:
            error = {
                "field": "policy_holder_dob",
                "error": "Invalid date format. Must be YYYY-MM-DD (e.g., 1985-05-15)",
                "received_value": policy_holder_dob
            }
            validation_errors.append(error)
            is_valid = False
            logger.warning(f"Validation error: {error}")

    # ===== 6. RELATIONSHIP TO PATIENT VALIDATION =====
    relationship = insurance_data.get("relationship_to_patient", "").strip().lower()
    logger.debug(f"Validating relationship to patient: '{relationship}'")

    if not relationship:
        error = {
            "field": "relationship_to_patient",
            "error": "Relationship to patient is required",
            "received_value": relationship
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    elif relationship not in VALID_RELATIONSHIPS:
        error = {
            "field": "relationship_to_patient",
            "error": f"Invalid relationship. Must be one of: {', '.join(VALID_RELATIONSHIPS)}",
            "received_value": relationship
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    else:
        logger.info(f"Relationship valid: {relationship}")

    # ===== 7. EFFECTIVE DATE VALIDATION =====
    effective_date = insurance_data.get("effective_date", "")
    logger.debug(f"Validating effective date: '{effective_date}'")

    if not effective_date:
        error = {
            "field": "effective_date",
            "error": "Policy effective date is required",
            "received_value": effective_date
        }
        validation_errors.append(error)
        is_valid = False
        logger.warning(f"Validation error: {error}")
    else:
        try:
            effective_date_obj = datetime.strptime(effective_date, "%Y-%m-%d")
            logger.info(f"Effective date valid: {effective_date}")

            # Check if policy is currently active
            if effective_date_obj > datetime.now():
                validation_errors.append({
                    "field": "effective_date",
                    "error": "Warning: Policy is not yet effective",
                    "received_value": effective_date,
                    "severity": "warning"
                })
                logger.warning(f"Policy not yet effective: {effective_date}")

        except ValueError:
            error = {
                "field": "effective_date",
                "error": "Invalid date format. Must be YYYY-MM-DD (e.g., 2025-01-01)",
                "received_value": effective_date
            }
            validation_errors.append(error)
            is_valid = False
            logger.warning(f"Validation error: {error}")

    # ===== 8. EXPIRATION DATE VALIDATION (OPTIONAL) =====
    expiration_date = insurance_data.get("expiration_date", "")
    if expiration_date:
        logger.debug(f"Validating expiration date: '{expiration_date}'")
        try:
            expiration_date_obj = datetime.strptime(expiration_date, "%Y-%m-%d")

            # Check if policy has expired
            if expiration_date_obj < datetime.now():
                error = {
                    "field": "expiration_date",
                    "error": "Policy has expired",
                    "received_value": expiration_date
                }
                validation_errors.append(error)
                is_valid = False
                logger.warning(f"Validation error: {error}")

            # Check if expiration is after effective date
            if effective_date:
                try:
                    effective_date_obj = datetime.strptime(effective_date, "%Y-%m-%d")
                    if expiration_date_obj <= effective_date_obj:
                        error = {
                            "field": "expiration_date",
                            "error": "Expiration date must be after effective date",
                            "received_value": expiration_date
                        }
                        validation_errors.append(error)
                        is_valid = False
                        logger.warning(f"Validation error: {error}")
                    else:
                        logger.info(f"Expiration date valid: {expiration_date}")
                except ValueError:
                    pass  # Already caught in effective_date validation

        except ValueError:
            error = {
                "field": "expiration_date",
                "error": "Invalid date format. Must be YYYY-MM-DD (e.g., 2026-12-31)",
                "received_value": expiration_date
            }
            validation_errors.append(error)
            is_valid = False
            logger.warning(f"Validation error: {error}")

    # ===== STEP 9: PROVIDER VERIFICATION (CSV LOOKUP) =====
    # Only verify with provider if format validation passed
    provider_verification_result = None

    if is_valid:
        logger.info("=" * 80)
        logger.info("STEP 9: VERIFYING WITH INSURANCE PROVIDER")
        logger.info("=" * 80)

        try:
            # Verify with insurance provider using CSV lookup
            provider_verification_result = verify_insurance_with_provider(
                provider_name=provider_name,
                policy_number=policy_number,
                policy_holder_name=policy_holder_name,
                policy_holder_dob=policy_holder_dob,
                use_llm_detection=True
            )

            logger.info(f"Provider verification status: {provider_verification_result['verification_status']}")
            logger.info(f"Policy found: {provider_verification_result['policy_found']}")
            logger.info(f"Is verified: {provider_verification_result['is_verified']}")

            # If provider verification failed, add errors
            if not provider_verification_result['is_verified']:
                is_valid = False

                # Add provider verification errors
                for error in provider_verification_result.get('errors', []):
                    validation_errors.append({
                        "field": "provider_verification",
                        "error": error,
                        "severity": "error"
                    })
                    logger.error(f"Provider verification error: {error}")

                # Add warnings
                for warning in provider_verification_result.get('warnings', []):
                    validation_errors.append({
                        "field": "provider_verification",
                        "error": warning,
                        "severity": "warning"
                    })
                    logger.warning(f"Provider verification warning: {warning}")
            else:
                logger.info("✅ Provider verification SUCCESSFUL")

        except Exception as e:
            logger.error(f"Error during provider verification: {e}", exc_info=True)
            # Don't fail validation if provider verification service has issues
            validation_errors.append({
                "field": "provider_verification",
                "error": f"Unable to verify with insurance provider: {str(e)}",
                "severity": "warning"
            })

    # ===== VALIDATION SUMMARY =====
    if is_valid:
        logger.info(f"✅ Insurance validation PASSED for patient {state['patient_id']}")
        message = "Insurance details validated successfully and verified with insurance provider"

        # Filter out warnings
        warning_errors = [e for e in validation_errors if e.get("severity") == "warning"]
        if warning_errors:
            logger.info(f"Validation passed with {len(warning_errors)} warnings")
    else:
        error_count = len([e for e in validation_errors if e.get("severity") != "warning"])
        logger.error(f"❌ Insurance validation FAILED for patient {state['patient_id']} - {error_count} error(s)")
        message = f"Insurance validation failed with {error_count} error(s)"

    # Create notification
    notification = {
        "id": f"insurance_validation_{datetime.now().timestamp()}",
        "type": "success" if is_valid else "error",
        "priority": PriorityLevel.HIGH.value if not is_valid else PriorityLevel.MEDIUM.value,
        "title": "Insurance Validation" + (" Complete" if is_valid else " Failed"),
        "message": message,
        "timestamp": datetime.now(),
    }

    if not is_valid:
        notification["validation_errors"] = validation_errors

    # Update state
    updated_state = {
        **state,
        "insurance_verified": is_valid,
        "insurance_validation_errors": validation_errors if not is_valid else None,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }

    # Save insurance details in state if valid
    if is_valid:
        insurance_details = {
            **insurance_data,
            "validated_at": datetime.now().isoformat(),
            "validated": True
        }

        # Add provider verification details if available
        if provider_verification_result and provider_verification_result.get('is_verified'):
            insurance_details["provider_verification"] = {
                "verified_with_provider": True,
                "provider_detected": provider_verification_result['provider_detection']['detected_provider'],
                "detection_confidence": provider_verification_result['provider_detection']['confidence'],
                "verification_details": provider_verification_result.get('verification_details', {}),
                "verified_at": provider_verification_result.get('verified_at')
            }

        updated_state["insurance_details"] = insurance_details
        logger.info(f"Insurance details saved to state for patient {state['patient_id']}")

    return updated_state
