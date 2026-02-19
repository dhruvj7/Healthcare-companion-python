import logging
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.database.token_store import get_token, save_token, delete_token

logger = logging.getLogger(__name__)


async def get_credentials(patient_email: str) -> Credentials | None:
    """Load and auto-refresh credentials for a patient."""
    token_data = await get_token(patient_email)
    if not token_data:
        return None  # Patient hasn't authorized yet

    creds = Credentials(
        token=token_data["token"],
        refresh_token=token_data["refresh_token"],
        token_uri=token_data["token_uri"],
        client_id=token_data["client_id"],
        client_secret=token_data["client_secret"],
        scopes=token_data["scopes"]
    )

    # Auto-refresh if token is expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save the refreshed token back to DB
        await save_token(patient_email, {
            "token":         creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri":     creds.token_uri,
            "client_id":     creds.client_id,
            "client_secret": creds.client_secret,
            "scopes":        list(creds.scopes)
        })

    return creds


async def block_calendar(appointment_details: dict) -> str | None:
    """
    Creates a Google Calendar event on the patient's calendar.
    Returns the event ID if successful, None if patient hasn't authorized.
    """
    patient_email = appointment_details["patient_email"]
    creds = await get_credentials(patient_email)

    if not creds:
        logger.warning(f"⚠️ No OAuth token for {patient_email}. Skipping calendar block.")
        return None

    # Build datetime objects
    start_dt = datetime.strptime(
        f"{appointment_details['date']} {appointment_details['time']}",
        "%Y-%m-%d %H:%M"
    )
    end_dt = start_dt + timedelta(minutes=appointment_details["duration"])

    event_body = {
        "summary": f"Appointment with Dr. {appointment_details['doctor']}",
        "location": appointment_details["location"],
        "description": (
            f"Specialty: {appointment_details['specialty']}\n"
            f"Reason: {appointment_details['reason_for_visit']}\n"
            f"Booking ID: {appointment_details['booking_id']}\n"
            f"Type: {appointment_details['appointment_type']}"
        ),
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "UTC"  # adjust to your clinic's timezone
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "UTC"
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email",  "minutes": 24 * 60},  # 1 day before
                {"method": "popup",  "minutes": 30},        # 30 mins before
            ]
        },
        "status": "confirmed"
    }

    service = build("calendar", "v3", credentials=creds)
    event = service.events().insert(
        calendarId="primary",
        body=event_body
    ).execute()

    event_id = event.get("id")
    logger.info(f"📅 Calendar event created: {event_id} for {patient_email}")
    return event_id