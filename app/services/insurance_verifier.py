# app/services/insurance_verifier.py

"""
Insurance Policy Verification Service

Verifies insurance policies against CSV databases for different providers.
"""

import os
import csv
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.services.insurance_provider_detector import detect_provider

logger = logging.getLogger(__name__)

# Base path for insurance CSV files
INSURANCE_DATA_PATH = Path(__file__).parent.parent / "data" / "insurance"


class InsuranceVerificationResult:
    """Container for insurance verification results"""

    def __init__(
        self,
        is_verified: bool,
        policy_found: bool,
        verification_details: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None
    ):
        self.is_verified = is_verified
        self.policy_found = policy_found
        self.verification_details = verification_details or {}
        self.errors = errors or []
        self.warnings = warnings or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "is_verified": self.is_verified,
            "policy_found": self.policy_found,
            "verification_details": self.verification_details,
            "errors": self.errors,
            "warnings": self.warnings
        }


def load_insurance_csv(csv_filename: str) -> List[Dict[str, str]]:
    """
    Load insurance data from CSV file.

    Args:
        csv_filename: Name of the CSV file

    Returns:
        List of dictionaries containing policy records
    """
    csv_path = INSURANCE_DATA_PATH / csv_filename

    logger.info(f"Loading insurance data from: {csv_path}")

    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)

        logger.info(f"Loaded {len(records)} records from {csv_filename}")
        return records

    except Exception as e:
        logger.error(f"Error loading CSV file {csv_filename}: {e}", exc_info=True)
        return []


def verify_policy_in_csv(
    csv_filename: str,
    policy_number: str,
    policy_holder_name: str,
    policy_holder_dob: str
) -> InsuranceVerificationResult:
    """
    Verify a policy exists in the CSV file with matching details.

    Args:
        csv_filename: CSV file to search
        policy_number: Policy number to verify
        policy_holder_name: Policy holder's name
        policy_holder_dob: Policy holder's date of birth

    Returns:
        InsuranceVerificationResult object
    """
    logger.info(f"Verifying policy {policy_number} in {csv_filename}")

    # Load CSV data
    records = load_insurance_csv(csv_filename)

    if not records:
        return InsuranceVerificationResult(
            is_verified=False,
            policy_found=False,
            errors=["Unable to load insurance provider data"]
        )

    # Search for policy
    for record in records:
        if record.get("policy_number", "").upper() == policy_number.upper():
            logger.info(f"Policy found: {policy_number}")

            # Policy found, now verify details
            errors = []
            warnings = []
            is_verified = True

            # Check policy holder name (case-insensitive)
            csv_name = record.get("policy_holder_name", "").lower().strip()
            input_name = policy_holder_name.lower().strip()

            if csv_name != input_name:
                error = f"Policy holder name mismatch. Expected: {record.get('policy_holder_name')}, Got: {policy_holder_name}"
                errors.append(error)
                is_verified = False
                logger.warning(error)

            # Check DOB
            csv_dob = record.get("policy_holder_dob", "")
            if csv_dob != policy_holder_dob:
                error = f"Date of birth mismatch. Expected: {csv_dob}, Got: {policy_holder_dob}"
                errors.append(error)
                is_verified = False
                logger.warning(error)

            # Check policy status
            policy_status = record.get("status", "").lower()
            if policy_status != "active":
                error = f"Policy is not active. Current status: {policy_status}"
                errors.append(error)
                is_verified = False
                logger.warning(error)

            # Check expiration date
            expiration_date_str = record.get("expiration_date", "")
            if expiration_date_str:
                try:
                    expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d")
                    if expiration_date < datetime.now():
                        error = f"Policy has expired on {expiration_date_str}"
                        errors.append(error)
                        is_verified = False
                        logger.warning(error)
                except ValueError:
                    warnings.append(f"Could not parse expiration date: {expiration_date_str}")

            # Check effective date
            effective_date_str = record.get("effective_date", "")
            if effective_date_str:
                try:
                    effective_date = datetime.strptime(effective_date_str, "%Y-%m-%d")
                    if effective_date > datetime.now():
                        warning = f"Policy is not yet effective. Effective date: {effective_date_str}"
                        warnings.append(warning)
                        logger.info(warning)
                except ValueError:
                    warnings.append(f"Could not parse effective date: {effective_date_str}")

            # Prepare verification details
            verification_details = {
                "policy_number": record.get("policy_number"),
                "group_number": record.get("group_number"),
                "policy_holder_name": record.get("policy_holder_name"),
                "relationship": record.get("relationship"),
                "status": record.get("status"),
                "coverage_type": record.get("coverage_type"),
                "copay_amount": record.get("copay_amount"),
                "effective_date": record.get("effective_date"),
                "expiration_date": record.get("expiration_date"),
                "verification_timestamp": datetime.now().isoformat(),
                "verified_fields": {
                    "policy_number": True,
                    "policy_holder_name": csv_name == input_name,
                    "policy_holder_dob": csv_dob == policy_holder_dob,
                    "status": policy_status == "active"
                }
            }

            result = InsuranceVerificationResult(
                is_verified=is_verified,
                policy_found=True,
                verification_details=verification_details,
                errors=errors,
                warnings=warnings
            )

            if is_verified:
                logger.info(f"✅ Policy {policy_number} successfully verified")
            else:
                logger.warning(f"❌ Policy {policy_number} found but verification failed: {errors}")

            return result

    # Policy not found
    logger.warning(f"Policy {policy_number} not found in {csv_filename}")

    return InsuranceVerificationResult(
        is_verified=False,
        policy_found=False,
        errors=[f"Policy number {policy_number} not found in our records"]
    )


def verify_insurance(
    provider_name: str,
    policy_number: str,
    policy_holder_name: str,
    policy_holder_dob: str,
    use_llm_detection: bool = True
) -> Dict[str, Any]:
    """
    Main entry point for insurance verification.

    Steps:
    1. Detect insurance provider using LLM/rules
    2. Load appropriate CSV file
    3. Verify policy exists and matches details

    Args:
        provider_name: Insurance provider name
        policy_number: Policy number
        policy_holder_name: Policy holder's name
        policy_holder_dob: Policy holder's DOB (YYYY-MM-DD)
        use_llm_detection: Whether to use LLM for provider detection

    Returns:
        Dict containing verification results
    """
    logger.info(f"Starting insurance verification for policy {policy_number}")
    logger.info(f"Provider: {provider_name}, Holder: {policy_holder_name}")

    # Step 1: Detect provider
    detection_result = detect_provider(provider_name, use_llm=use_llm_detection)

    logger.info(f"Provider detection result: {detection_result['detected_provider']} "
                f"(confidence: {detection_result['confidence']})")

    if detection_result["detected_provider"] == "unknown" or not detection_result["csv_filename"]:
        logger.error(f"Could not determine provider for: {provider_name}")
        return {
            "verification_status": "error",
            "is_verified": False,
            "policy_found": False,
            "provider_detection": detection_result,
            "errors": [f"Could not identify insurance provider: {provider_name}"],
            "message": "Unable to verify insurance: Provider not recognized"
        }

    # Step 2: Verify policy in CSV
    verification_result = verify_policy_in_csv(
        csv_filename=detection_result["csv_filename"],
        policy_number=policy_number,
        policy_holder_name=policy_holder_name,
        policy_holder_dob=policy_holder_dob
    )

    # Step 3: Build response
    response = {
        "verification_status": "success" if verification_result.is_verified else "failed",
        "is_verified": verification_result.is_verified,
        "policy_found": verification_result.policy_found,
        "provider_detection": detection_result,
        "verification_details": verification_result.verification_details,
        "errors": verification_result.errors,
        "warnings": verification_result.warnings,
        "verified_at": datetime.now().isoformat()
    }

    # Add user-friendly message
    if verification_result.is_verified:
        response["message"] = "✅ Insurance policy successfully verified with provider"
    elif verification_result.policy_found:
        response["message"] = "❌ Policy found but verification failed: " + "; ".join(verification_result.errors)
    else:
        response["message"] = "❌ Policy not found in provider records"

    logger.info(f"Verification complete: {response['verification_status']}")

    return response


def get_policy_details(provider_name: str, policy_number: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed policy information without full verification.

    Args:
        provider_name: Insurance provider name
        policy_number: Policy number

    Returns:
        Policy details dict or None if not found
    """
    logger.info(f"Fetching policy details for {policy_number} from {provider_name}")

    # Detect provider
    detection_result = detect_provider(provider_name, use_llm=True)

    if not detection_result["csv_filename"]:
        logger.warning(f"Provider not recognized: {provider_name}")
        return None

    # Load CSV
    records = load_insurance_csv(detection_result["csv_filename"])

    # Find policy
    for record in records:
        if record.get("policy_number", "").upper() == policy_number.upper():
            logger.info(f"Policy details found for {policy_number}")
            return dict(record)

    logger.warning(f"Policy {policy_number} not found")
    return None
