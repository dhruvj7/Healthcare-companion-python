# app/agents/appointment_scheduler/node.py

import logging
import aiosqlite
from pathlib import Path
from typing import Dict, Any

from app.agents.appointment_scheduler.crud import book_appointment
from app.services.email_service import send_confirmation_emails

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "database" / "appointments.db"


async def appointment_booking_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent-callable node for appointment booking.

    Extracts booking details from state, books appointment, sends confirmation emails,
    and returns updated state with booking status.

    Required state fields:
        - slot_id: int
        - patient_name: str
        - patient_email: str
        - patient_phone: str
        - reason_for_visit: str
        - appointment_type: str (default: "in-person")

    Returns:
        Updated state with:
            - booking_status: "confirmed" | "error"
            - booking_id: str (if successful)
            - appointment_details: dict (if successful)
            - confirmation_message: str
            - error: str (if failed)
    """

    logger.info("🔷 Appointment booking node started")

    try:
        # Extract required booking fields from state
        slot_id = state.get("slot_id")
        patient_name = state.get("patient_name")
        patient_email = state.get("patient_email")
        patient_phone = state.get("patient_phone")
        reason_for_visit = state.get("reason_for_visit", "General consultation")
        appointment_type = state.get("appointment_type", "in-person")

        # Validate required fields
        if not all([slot_id, patient_name, patient_email, patient_phone]):
            logger.error("❌ Missing required booking fields")
            return {
                **state,
                "booking_status": "error",
                "error": "Missing required fields: slot_id, patient_name, patient_email, patient_phone",
                "confirmation_message": "Unable to book appointment. Please provide all required information."
            }

        logger.info(f"📋 Booking request - Slot ID: {slot_id}, Patient: {patient_name}")

        # Connect to database and book appointment
        async with aiosqlite.connect(DATABASE_PATH) as db:
            db.row_factory = aiosqlite.Row

            # Call existing booking service
            appointment_data = await book_appointment(
                db=db,
                slot_id=slot_id,
                patient_name=patient_name,
                patient_email=patient_email,
                patient_phone=patient_phone,
                reason_for_visit=reason_for_visit,
                appointment_type=appointment_type
            )

        logger.info(f"✅ Appointment booked - Booking ID: {appointment_data['booking_id']}")

        # Send confirmation emails
        emails_sent = await send_confirmation_emails(appointment_data)

        if emails_sent:
            logger.info(f"📧 Confirmation emails sent for booking {appointment_data['booking_id']}")
        else:
            logger.warning(f"⚠️ Failed to send some emails for booking {appointment_data['booking_id']}")

        # Build appointment details for response
        slot = appointment_data['slot']
        appointment_details = {
            "booking_id": appointment_data['booking_id'],
            "date": slot['slot_date'],
            "time": slot['slot_time'],
            "doctor": slot['doctor_name'],
            "specialty": slot['doctor_specialty'],
            "location": slot['location'],
            "duration": slot['duration_minutes'],
            "appointment_type": appointment_type,
            "patient_name": patient_name,
            "patient_email": patient_email,
            "patient_phone": patient_phone,
            "reason_for_visit": reason_for_visit
        }

        confirmation_message = (
            f"Appointment booked successfully! "
            f"Booking ID: {appointment_data['booking_id']}. "
            f"You will see Dr. {slot['doctor_name']} on {slot['slot_date']} at {slot['slot_time']}. "
            f"Confirmation emails have been sent to patient and doctor."
        )

        logger.info("✅ Appointment booking node completed successfully")

        # Return updated state
        return {
            **state,
            "booking_status": "confirmed",
            "booking_id": appointment_data['booking_id'],
            "appointment_details": appointment_details,
            "confirmation_message": confirmation_message,
            "emails_sent": emails_sent
        }

    except ValueError as e:
        # Handle booking validation errors (slot not found, already booked, etc.)
        logger.error(f"❌ Booking validation error: {str(e)}")
        return {
            **state,
            "booking_status": "error",
            "error": str(e),
            "confirmation_message": f"Unable to book appointment: {str(e)}"
        }

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"❌ Unexpected error in booking node: {str(e)}", exc_info=True)
        return {
            **state,
            "booking_status": "error",
            "error": "Internal server error during booking",
            "confirmation_message": "An unexpected error occurred. Please try again later."
        }