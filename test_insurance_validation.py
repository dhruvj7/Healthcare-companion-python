"""
Test script for insurance validation endpoint

This script demonstrates the insurance validation functionality with both valid and invalid examples.
"""

import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"


def initialize_session():
    """Initialize a hospital journey session"""
    print("=" * 80)
    print("STEP 1: Initializing Hospital Journey Session")
    print("=" * 80)

    payload = {
        "patient_id": "P123456",
        "appointment_id": "APT789",
        "doctor_name": "Dr. Sarah Smith",
        "appointment_time": (datetime.now() + timedelta(hours=1)).isoformat(),
        "department": "Cardiology",
        "reason_for_visit": "Follow-up for chest pain",
        "language": "en"
    }

    response = requests.post(f"{BASE_URL}/initialize", json=payload)

    if response.status_code == 201:
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session initialized successfully: {session_id}")
        print(json.dumps(session_data, indent=2))
        return session_id
    else:
        print(f"❌ Failed to initialize session: {response.status_code}")
        print(response.text)
        return None


def test_valid_insurance(session_id):
    """Test with valid insurance details"""
    print("\n" + "=" * 80)
    print("STEP 2: Testing VALID Insurance Details")
    print("=" * 80)

    payload = {
        "provider_name": "Blue Cross Blue Shield",
        "policy_number": "ABC123456789",
        "group_number": "GRP001",
        "policy_holder_name": "John Doe",
        "policy_holder_dob": "1985-05-15",
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01",
        "expiration_date": "2026-12-31"
    }

    print("\nPayload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=payload
    )

    print(f"\nResponse Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, default=str))


def test_invalid_insurance_missing_fields(session_id):
    """Test with missing required fields"""
    print("\n" + "=" * 80)
    print("STEP 3: Testing INVALID Insurance - Missing Fields")
    print("=" * 80)

    payload = {
        "provider_name": "",  # Empty
        "policy_number": "123",  # Too short
        "policy_holder_name": "John Doe",
        "policy_holder_dob": "1985-05-15",
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01"
    }

    print("\nPayload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=payload
    )

    print(f"\nResponse Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, default=str))


def test_invalid_insurance_dates(session_id):
    """Test with invalid dates"""
    print("\n" + "=" * 80)
    print("STEP 4: Testing INVALID Insurance - Invalid Dates")
    print("=" * 80)

    future_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
    past_date = "2020-01-01"

    payload = {
        "provider_name": "Aetna",
        "policy_number": "XYZ987654321",
        "policy_holder_name": "Jane Smith",
        "policy_holder_dob": future_date,  # Future DOB - invalid
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01",
        "expiration_date": past_date  # Expired - invalid
    }

    print("\nPayload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=payload
    )

    print(f"\nResponse Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, default=str))


def test_invalid_relationship(session_id):
    """Test with invalid relationship"""
    print("\n" + "=" * 80)
    print("STEP 5: Testing INVALID Insurance - Invalid Relationship")
    print("=" * 80)

    payload = {
        "provider_name": "United Healthcare",
        "policy_number": "UHC123456789",
        "policy_holder_name": "Bob Johnson",
        "policy_holder_dob": "1980-03-20",
        "relationship_to_patient": "cousin",  # Invalid relationship
        "effective_date": "2024-01-01",
        "expiration_date": "2026-12-31"
    }

    print("\nPayload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=payload
    )

    print(f"\nResponse Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, default=str))


def test_unrecognized_provider(session_id):
    """Test with unrecognized provider (warning, not error)"""
    print("\n" + "=" * 80)
    print("STEP 6: Testing Unrecognized Provider (Warning)")
    print("=" * 80)

    payload = {
        "provider_name": "ABC Insurance Company",  # Not in recognized list
        "policy_number": "ABC123456789",
        "policy_holder_name": "Alice Brown",
        "policy_holder_dob": "1990-08-10",
        "relationship_to_patient": "self",
        "effective_date": "2025-01-01",
        "expiration_date": "2026-12-31"
    }

    print("\nPayload:")
    print(json.dumps(payload, indent=2))

    response = requests.post(
        f"{BASE_URL}/insurance/validate/{session_id}",
        json=payload
    )

    print(f"\nResponse Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, default=str))


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("INSURANCE VALIDATION TEST SUITE")
    print("=" * 80)

    # Initialize session
    session_id = initialize_session()

    if not session_id:
        print("\n❌ Cannot proceed without a valid session ID")
        return

    # Run tests
    test_valid_insurance(session_id)
    test_invalid_insurance_missing_fields(session_id)
    test_invalid_insurance_dates(session_id)
    test_invalid_relationship(session_id)
    test_unrecognized_provider(session_id)

    print("\n" + "=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to the server.")
        print("Please make sure the FastAPI server is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
