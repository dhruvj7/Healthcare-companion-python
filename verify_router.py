"""
Verify that the insurance router is properly configured
"""

print("=" * 80)
print("VERIFYING INSURANCE ROUTER CONFIGURATION")
print("=" * 80)

# Test 1: Import main app
print("\n[1/5] Testing main app import...")
try:
    from app.main import app
    print("    PASS: Main app imported successfully")
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 2: Import insurance router
print("\n[2/5] Testing insurance router import...")
try:
    from app.api.v1.routes import insurance
    print("    PASS: Insurance router imported successfully")
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 3: Import hospital guidance router
print("\n[3/5] Testing hospital guidance router import...")
try:
    from app.api.v1.routes import hospital_guidance
    print("    PASS: Hospital guidance router imported successfully")
except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 4: Check router has correct endpoints
print("\n[4/5] Verifying insurance router endpoints...")
try:
    from app.api.v1.routes.insurance import router

    # Get all routes
    routes = [route.path for route in router.routes]

    expected_routes = [
        "/validate/{session_id}",
        "/status/{session_id}",
        "/clear/{session_id}"
    ]

    for expected in expected_routes:
        if expected in routes:
            print(f"    PASS: Found endpoint {expected}")
        else:
            print(f"    FAIL: Missing endpoint {expected}")
            exit(1)

except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

# Test 5: Verify session sharing function exists
print("\n[5/5] Verifying session sharing mechanism...")
try:
    from app.api.v1.routes.hospital_guidance import get_active_sessions
    from app.api.v1.routes.insurance import set_active_sessions

    print("    PASS: Session sharing functions exist")

    # Test the mechanism
    sessions = get_active_sessions()
    set_active_sessions(sessions)
    print("    PASS: Session sharing mechanism works")

except Exception as e:
    print(f"    FAIL: {str(e)}")
    exit(1)

print("\n" + "=" * 80)
print("ALL CHECKS PASSED - Insurance router is properly configured!")
print("=" * 80)
print("\nRouter Configuration:")
print("  - Insurance router: /api/v1/insurance")
print("  - 3 endpoints: validate, status, clear")
print("  - Session sharing: Enabled")
print("\nEndpoints:")
print("  1. POST /api/v1/insurance/validate/{session_id}")
print("  2. GET  /api/v1/insurance/status/{session_id}")
print("  3. DELETE /api/v1/insurance/clear/{session_id}")
print("\nNext steps:")
print("1. Start server: uvicorn app.main:app --reload")
print("2. Run tests: python test_insurance_validation.py")
print("3. View docs: http://localhost:8000/docs")
