"""
Verify that the insurance validation feature is properly installed
"""

print("=" * 80)
print("VERIFYING INSURANCE VALIDATION INSTALLATION")
print("=" * 80)

# Test 1: Import models
print("\n[1/4] Testing model imports...")
try:
    from app.models.hospital_models import InsuranceValidationRequest, InsuranceValidationResponse
    print("    PASS: Models imported successfully")
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 2: Import validation function
print("\n[2/4] Testing validation function import...")
try:
    from app.agents.hospital_guidance.nodes.insurance_validation import validate_insurance
    print("    PASS: Validation function imported successfully")
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 3: Import state
print("\n[3/4] Testing state import...")
try:
    from app.agents.hospital_guidance.state import HospitalGuidanceState
    print("    PASS: State imported successfully")
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 4: Verify state has insurance fields
print("\n[4/4] Verifying state structure...")
try:
    from typing import get_type_hints
    hints = get_type_hints(HospitalGuidanceState)

    required_fields = ['insurance_details', 'insurance_validation_errors']
    for field in required_fields:
        if field in hints:
            print(f"    PASS: State has '{field}' field")
        else:
            print(f"    FAIL: State missing '{field}' field")
            exit(1)
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

print("\n" + "=" * 80)
print("ALL CHECKS PASSED - Insurance validation feature is properly installed!")
print("=" * 80)
print("\nNext steps:")
print("1. Start the server: uvicorn app.main:app --reload")
print("2. Run tests: python test_insurance_validation.py")
print("3. View API docs: http://localhost:8000/docs")
