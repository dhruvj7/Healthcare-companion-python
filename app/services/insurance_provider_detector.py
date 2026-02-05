# app/services/insurance_provider_detector.py

"""
Insurance Provider Detection Service

Uses LLM to intelligently detect which insurance provider CSV file to query
based on the provider name provided by the user.
"""

import logging
import json
import re
from typing import Optional, Dict, Any
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

# Mapping of canonical provider names to CSV filenames
PROVIDER_CSV_MAPPING = {
    "blue_cross_blue_shield": "blue_cross_blue_shield.csv",
    "bcbs": "blue_cross_blue_shield.csv",
    "aetna": "aetna.csv",
    "united_healthcare": "united_healthcare.csv",
    "uhc": "united_healthcare.csv",
    "cigna": "cigna.csv",
    "humana": "humana.csv",
    "kaiser_permanente": "kaiser.csv",
    "kaiser": "kaiser.csv",
    "anthem": "anthem.csv",
    "medicare": "medicare.csv",
    "medicaid": "medicaid.csv"
}

# Provider aliases for better matching
PROVIDER_ALIASES = {
    "blue cross blue shield": "blue_cross_blue_shield",
    "bcbs": "bcbs",
    "blue cross": "bcbs",
    "blue shield": "bcbs",
    "aetna": "aetna",
    "united healthcare": "united_healthcare",
    "united": "united_healthcare",
    "uhc": "uhc",
    "cigna": "cigna",
    "humana": "humana",
    "kaiser permanente": "kaiser_permanente",
    "kaiser": "kaiser",
    "anthem": "anthem",
    "wellpoint": "anthem",
    "medicare": "medicare",
    "medicaid": "medicaid"
}


def detect_provider_with_llm(provider_name: str) -> Dict[str, Any]:
    """
    Use LLM to intelligently detect the insurance provider and determine
    which CSV file to query.

    Args:
        provider_name: The provider name from user input

    Returns:
        Dict containing:
        - detected_provider: Canonical provider name
        - csv_filename: CSV file to query
        - confidence: Confidence score (0-1)
        - reasoning: LLM's reasoning
    """
    logger.info(f"Using LLM to detect provider for: '{provider_name}'")

    llm = get_llm()

    prompt = f"""
You are an insurance provider identification expert. Your task is to identify which insurance provider
the user is referring to and map it to the correct database.

User provided provider name: "{provider_name}"

Available providers in our system:
1. Blue Cross Blue Shield (BCBS) - aliases: "Blue Cross", "Blue Shield", "BCBS"
2. Aetna
3. United Healthcare (UHC) - aliases: "United", "UHC"
4. Cigna
5. Humana
6. Kaiser Permanente - aliases: "Kaiser"
7. Anthem - aliases: "Wellpoint"
8. Medicare
9. Medicaid

Analyze the provider name and determine:
1. Which provider it matches
2. How confident you are (0.0 to 1.0)
3. Brief reasoning

Respond ONLY with valid JSON:
{{
  "detected_provider": "blue_cross_blue_shield",
  "confidence": 0.95,
  "reasoning": "User mentioned 'Blue Cross' which clearly refers to Blue Cross Blue Shield"
}}

Valid provider values:
- blue_cross_blue_shield
- aetna
- united_healthcare
- cigna
- humana
- kaiser_permanente
- anthem
- medicare
- medicaid
- unknown (if cannot determine)
"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Remove markdown code blocks if present
        content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE)

        result = json.loads(content)

        detected_provider = result.get("detected_provider", "unknown")
        confidence = result.get("confidence", 0.0)
        reasoning = result.get("reasoning", "")

        logger.info(f"LLM detected provider: {detected_provider} (confidence: {confidence})")
        logger.info(f"LLM reasoning: {reasoning}")

        # Get CSV filename
        csv_filename = PROVIDER_CSV_MAPPING.get(detected_provider)

        if not csv_filename:
            logger.warning(f"No CSV mapping found for detected provider: {detected_provider}")
            csv_filename = None

        return {
            "detected_provider": detected_provider,
            "csv_filename": csv_filename,
            "confidence": confidence,
            "reasoning": reasoning,
            "detection_method": "llm"
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Raw response: {content}")
        # Fall back to rule-based detection
        return detect_provider_rule_based(provider_name)

    except Exception as e:
        logger.error(f"Error during LLM provider detection: {e}", exc_info=True)
        # Fall back to rule-based detection
        return detect_provider_rule_based(provider_name)


def detect_provider_rule_based(provider_name: str) -> Dict[str, Any]:
    """
    Rule-based fallback for provider detection.

    Args:
        provider_name: The provider name from user input

    Returns:
        Dict containing detection results
    """
    logger.info(f"Using rule-based detection for: '{provider_name}'")

    provider_lower = provider_name.lower().strip()

    # Check exact matches first
    if provider_lower in PROVIDER_ALIASES:
        canonical_name = PROVIDER_ALIASES[provider_lower]
        csv_filename = PROVIDER_CSV_MAPPING.get(canonical_name)

        logger.info(f"Rule-based: Exact match found - {canonical_name}")

        return {
            "detected_provider": canonical_name,
            "csv_filename": csv_filename,
            "confidence": 1.0,
            "reasoning": f"Exact match found for '{provider_name}'",
            "detection_method": "rule_based_exact"
        }

    # Check partial matches
    for alias, canonical in PROVIDER_ALIASES.items():
        if alias in provider_lower or provider_lower in alias:
            csv_filename = PROVIDER_CSV_MAPPING.get(canonical)

            logger.info(f"Rule-based: Partial match found - {canonical}")

            return {
                "detected_provider": canonical,
                "csv_filename": csv_filename,
                "confidence": 0.8,
                "reasoning": f"Partial match found: '{alias}' in '{provider_name}'",
                "detection_method": "rule_based_partial"
            }

    # No match found
    logger.warning(f"No provider match found for: '{provider_name}'")

    return {
        "detected_provider": "unknown",
        "csv_filename": None,
        "confidence": 0.0,
        "reasoning": f"Could not match '{provider_name}' to any known provider",
        "detection_method": "rule_based_no_match"
    }


def detect_provider(provider_name: str, use_llm: bool = True) -> Dict[str, Any]:
    """
    Main entry point for provider detection.

    Uses LLM by default, falls back to rule-based if LLM fails.

    Args:
        provider_name: The provider name from user input
        use_llm: Whether to use LLM (default: True)

    Returns:
        Dict containing detection results
    """
    logger.info(f"Detecting provider for: '{provider_name}' (use_llm={use_llm})")

    if not provider_name or not provider_name.strip():
        logger.error("Empty provider name provided")
        return {
            "detected_provider": "unknown",
            "csv_filename": None,
            "confidence": 0.0,
            "reasoning": "No provider name provided",
            "detection_method": "error"
        }

    if use_llm:
        # Try LLM first
        result = detect_provider_with_llm(provider_name)

        # If LLM has low confidence, also try rule-based as backup
        if result["confidence"] < 0.6:
            logger.info("LLM confidence low, trying rule-based as well")
            rule_result = detect_provider_rule_based(provider_name)

            # Use whichever has higher confidence
            if rule_result["confidence"] > result["confidence"]:
                logger.info("Rule-based detection has higher confidence, using it")
                return rule_result

        return result
    else:
        # Use rule-based only
        return detect_provider_rule_based(provider_name)


def get_available_providers() -> list:
    """
    Get list of all available providers with CSV files.

    Returns:
        List of provider information dicts
    """
    providers = []

    for canonical_name, csv_file in PROVIDER_CSV_MAPPING.items():
        # Skip aliases (entries with same CSV file)
        if canonical_name in ["bcbs", "uhc", "kaiser"]:
            continue

        providers.append({
            "canonical_name": canonical_name,
            "display_name": canonical_name.replace("_", " ").title(),
            "csv_filename": csv_file
        })

    return providers
