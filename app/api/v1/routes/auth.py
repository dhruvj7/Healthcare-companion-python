import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from app.database.token_store import save_token, delete_token

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
REDIRECT_URI = "http://localhost:8000/auth/google/callback"  # update for prod


def build_flow() -> Flow:
    return Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )


@router.get("/google/login")
async def google_login(patient_email: str):
    """
    Step 1: Redirect patient to Google's consent screen.
    Call this before booking if the patient hasn't authorized yet.
    
    Example: GET /auth/google/login?patient_email=john@example.com
    """
    flow = build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",    # gets refresh_token so we can act later
        prompt="consent",         # force consent to always get refresh_token
        state=patient_email       # carry email through the redirect
    )
    return RedirectResponse(auth_url)


@router.get("/google/callback")
async def google_callback(code: str, state: str):
    """
    Step 2: Google redirects here after patient consents.
    We exchange the code for tokens and store them.
    """
    patient_email = state  # we passed email as state in Step 1

    try:
        flow = build_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Persist token for future use
        await save_token(patient_email, {
            "token":         credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri":     credentials.token_uri,
            "client_id":     credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes":        list(credentials.scopes)
        })

        return {"message": f"Calendar access granted for {patient_email}. You can now book appointments."}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")


@router.delete("/google/revoke")
async def revoke_access(patient_email: str):
    """Optional: Let patient disconnect their calendar."""
    await delete_token(patient_email)
    return {"message": f"Calendar access revoked for {patient_email}"}