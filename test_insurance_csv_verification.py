"""
Test script for Insurance CSV Verification System

Tests the complete flow:
1. Provider detection using LLM
2. CSV policy lookup
3. Full insurance validation with provider verification
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def test_list_providers():
    """Test listing available insurance providers"""
    print_section("TEST 1: List Available Insurance Providers")

    response = requests.get(f"{BASE_URL}/insurance/providers")

    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    return response.status_code == 200


def test_provider_detection():
    """Test LLM-based provider detection"""
    print_section("TEST 2: Provider Detection with LLM")

    test_cases = [
        "Blue Cross",
        "BCBS",
        "United",
        "Aetna",
        "Cigna Health",
        "Some Unknown Provider"
    ]

    for provider_name in test_cases:
        print(f"\nDetecting provider: '{provider_name}'")
        response = requests.post(
            f"{BASE_URL}/insurance/detect-provider",
            params={"provider_name": provider_name, "use_llm": True}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"  Detected: {result['detected_provider']}")
            print(f"  Confidence: {result['confidence']}")
            print(f"  CSV File: {result['csv_filename']}")
            print(f"  Method: {result['detection_method']}")
        else:
            print(f"  ERROR: {response.status_code}")


def test_policy_lookup():
    """Test policy lookup without full validation"""
    print_section("TEST 3: Policy Lookup")

    test_cases = [
        ("Blue Cross Blue Shield", "ABC123456789"),
        ("Aetna", "AET123456789"),
        ("United Healthcare", "UHC123456789"),
        ("Cigna", "CIG123456789"),
        ("Blue Cross", "INVALID_POLICY")
    ]

    for provider, policy_number in test_cases:
        print(f"\nLooking up: {provider} / {policy_number}")
        response = requests.get(
            f"{BASE_URL}/insurance/policy/{provider}/{policy_number}"
        )

        if response.status_code == 200:
            result = response.json()
            if result["policy_found"]:
                print(f"  ✅ Policy Found!")
                print(f"  Holder: {result['policy_details'].get('policy_holder_name')}")
                print(f"  Status: {result['policy_details'].get('status')}")
                print(f"  Coverage: {result['policy_details'].get('coverage_type')}")
            else:
                print(f"  ❌ Policy Not Found")
        else:
            print(f"  ERROR: {response.status_code}")


def test_full_validation_with_csv():
    """Test full validation flow with CSV verification"""
    print_section("TEST 4: Full Validation with CSV Verification")

    # Initialize session first
    print("\nStep 1: Initialize Session")
    init_response = requests.post(f"{BASE_URL}/initialize", json={
        "patient_id": "P123456",
        "appointment_id": "APT789",
        "doctor_name": "Dr. Sarah Smith",
        "appointment_time": (datetime.now() + timedelta(hours=1)).isoformat(),
        "department": "Cardiology",
        "reason_for_visit": "Follow-up"
    })

    if init_response.status_code != 201:
        print("❌ Failed to initialize session")
        return False

    session_id = init_response.json()["session_id"]
    print(f"✅ Session created: {session_id}")

    # Test Case 1: Valid policy that exists in CSV
    print("\nStep 2a: Validate with VALID policy (exists in CSV)")
    valid_request = {
        "provider_name": "Blue Cross Blue Shield",
        "policy_number": "ABC123456789",
        "group_number": "GRP001",
        "policy_holder_name": "John Doe",
        "policy_holder_dob": "1985-05-15",
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01",
        "expiration_date": "2026-12-31"
    }

    print("Request:", json.dumps(valid_request, indent=2))

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=valid_request
    )

    print(f"\nResponse Status: {response.status_code}")
    result = response.json()
    print(f"Is Valid: {result['is_valid']}")
    print(f"Insurance Verified: {result['insurance_verified']}")

    if result['validation_errors']:
        print(f"Errors: {len(result['validation_errors'])}")
        for error in result['validation_errors']:
            print(f"  - {error['field']}: {error['error']}")
    else:
        print("✅ No validation errors!")

    print(f"Message: {result['message']}")

    # Test Case 2: Policy not found in CSV
    print("\n\nStep 2b: Validate with INVALID policy (NOT in CSV)")
    invalid_request = {
        "provider_name": "Blue Cross Blue Shield",
        "policy_number": "INVALID999",
        "group_number": "GRP001",
        "policy_holder_name": "Jane Doe",
        "policy_holder_dob": "1990-01-01",
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01",
        "expiration_date": "2026-12-31"
    }

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=invalid_request
    )

    print(f"\nResponse Status: {response.status_code}")
    result = response.json()
    print(f"Is Valid: {result['is_valid']}")
    print(f"Insurance Verified: {result['insurance_verified']}")

    if result['validation_errors']:
        print(f"Errors: {len(result['validation_errors'])}")
        for error in result['validation_errors']:
            print(f"  - {error['field']}: {error['error']}")

    # Test Case 3: Wrong name for existing policy
    print("\n\nStep 2c: Validate with WRONG NAME (policy exists but name mismatch)")
    mismatch_request = {
        "provider_name": "Aetna",
        "policy_number": "AET123456789",  # This exists for "Thomas White"
        "group_number": "AGRP001",
        "policy_holder_name": "Wrong Name",  # Wrong name!
        "policy_holder_dob": "1983-04-12",  # Correct DOB
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01",
        "expiration_date": "2026-12-31"
    }

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=mismatch_request
    )

    print(f"\nResponse Status: {response.status_code}")
    result = response.json()
    print(f"Is Valid: {result['is_valid']}")
    print(f"Insurance Verified: {result['insurance_verified']}")

    if result['validation_errors']:
        print(f"Errors: {len(result['validation_errors'])}")
        for error in result['validation_errors']:
            print(f"  - {error['field']}: {error['error']}")

    return True


def test_insurance_status():
    """Test checking insurance verification status"""
    print_section("TEST 5: Check Insurance Status")

    # Need a session first
    init_response = requests.post(f"{BASE_URL}/initialize", json={
        "patient_id": "P999",
        "appointment_id": "APT999",
        "doctor_name": "Dr. Test",
        "appointment_time": (datetime.now() + timedelta(hours=1)).isoformat(),
        "department": "General",
        "reason_for_visit": "Checkup"
    })

    if init_response.status_code != 201:
        print("❌ Failed to initialize session")
        return False

    session_id = init_response.json()["session_id"]
    print(f"Session: {session_id}")

    # Validate insurance first
    requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json={
            "provider_name": "United Healthcare",
            "policy_number": "UHC123456789",
            "policy_holder_name": "Richard King",
            "policy_holder_dob": "1982-06-18",
            "relationship_to_patient": "self",
            "effective_date": "2025-01-01",
            "expiration_date": "2026-12-31"
        }
    )

    # Check status
    print("\nChecking insurance status...")
    response = requests.get(f"{BASE_URL}/insurance/status/{session_id}")

    if response.status_code == 200:
        result = response.json()
        print(f"Insurance Verified: {result['insurance_verified']}")
        print(f"Has Details: {result['has_insurance_details']}")
        if result.get('insurance_details'):
            print(f"Provider: {result['insurance_details'].get('provider_name')}")
            print(f"Holder: {result['insurance_details'].get('policy_holder_name')}")
    else:
        print(f"ERROR: {response.status_code}")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("INSURANCE CSV VERIFICATION TEST SUITE")
    print("=" * 80)

    try:
        test_list_providers()
        test_provider_detection()
        test_policy_lookup()
        test_full_validation_with_csv()
        test_insurance_status()

        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("Make sure the server is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
