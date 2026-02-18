# agents/appointment_scheduler/router.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import logging
import aiosqlite

from app.data.schemas.appointment import get_db_connection as get_db
from app.agents.appointment_scheduler.models import (
    DoctorResponse,
    AvailableSlotResponse,
    BookingRequest,
    BookingResponse
)
from app.agents.appointment_scheduler.crud import (
    get_all_doctors,
    get_available_slots,
    get_slot_details,
    book_appointment,
    get_appointment_by_booking_id
)
from app.services.email_service import send_confirmation_emails

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter(
    prefix="/appointment-scheduler",
    tags=["Appointment Scheduler"],
    responses={404: {"description": "Not found"}},
)


@router.get("/doctors", response_model=list[DoctorResponse])
async def list_doctors(
    city: Optional[str] = None,
    region: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = None,
    db: aiosqlite.Connection = Depends(get_db)
):
    """
    Get all available doctors, optionally filtered by location
    
    Query parameters:
    - city: Filter by city name
    - region: Filter by region
    - latitude: Latitude for proximity search
    - longitude: Longitude for proximity search
    - radius_km: Search radius in kilometers (requires latitude/longitude)
    
    Returns a list of doctors matching the filters.
    """
    
    doctors = await get_all_doctors(
        db,
        city=city,
        region=region,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
    return doctors


@router.get("/slots", response_model=list[AvailableSlotResponse])
async def list_available_slots(doctor_id: int = None, db: aiosqlite.Connection = Depends(get_db)):
    """
    Get all available appointment slots
    
    **Query Parameters:**
    - `doctor_id` (optional): Filter slots by specific doctor ID
    
    **Returns:**
    List of available time slots with doctor and location information
    """
    
    slots = await get_available_slots(db, doctor_id)
    return slots


@router.get("/slots/{slot_id}")
async def get_slot(slot_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """
    Get details of a specific appointment slot
    
    **Path Parameters:**
    - `slot_id`: The ID of the slot to retrieve
    
    **Returns:**
    Detailed information about the slot including availability status
    
    **Raises:**
    - 404: Slot not found
    - 400: Slot is already booked
    """
    
    slot = await get_slot_details(db, slot_id)
    
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    
    if slot['is_booked']:
        raise HTTPException(status_code=400, detail="Slot is already booked")
    
    return slot


@router.post("/book", response_model=BookingResponse)
async def create_booking(booking: BookingRequest, db: aiosqlite.Connection = Depends(get_db)):
    """
    Book an appointment
    
    **Request Body:**
    - `slot_id`: ID of the slot to book
    - `patient_name`: Patient's full name
    - `patient_email`: Patient's email address
    - `patient_phone`: Patient's phone number
    - `reason_for_visit`: Reason for the appointment
    - `appointment_type`: Either "in-person" or "telemedicine"
    
    **Returns:**
    Booking confirmation with appointment details
    
    **Process:**
    1. Books the selected time slot
    2. Marks slot as unavailable
    3. Sends confirmation emails to both patient and doctor
    
    **Raises:**
    - 400: Slot already booked or invalid data
    - 500: Internal server error
    """
    
    logger.info(f"📋 Booking request for slot {booking.slot_id} by {booking.patient_name}")
    
    try:
        # Book the appointment
        appointment_data = await book_appointment(
            db=db,
            slot_id=booking.slot_id,
            patient_name=booking.patient_name,
            patient_email=booking.patient_email,
            patient_phone=booking.patient_phone,
            reason_for_visit=booking.reason_for_visit,
            appointment_type=booking.appointment_type
        )
        
        logger.info(f"✅ Appointment booked: {appointment_data['booking_id']}")
        
        # Send confirmation emails
        emails_sent = await send_confirmation_emails(appointment_data)
        
        if emails_sent:
            logger.info(f"📧 Confirmation emails sent for booking {appointment_data['booking_id']}")
        else:
            logger.warning(f"⚠️  Failed to send some emails for booking {appointment_data['booking_id']}")
        
        return BookingResponse(
            booking_id=appointment_data['booking_id'],
            status="confirmed",
            message=f"Appointment booked successfully! Confirmation emails sent to patient and doctor.",
            appointment_details={
                "date": appointment_data['slot']['slot_date'],
                "time": appointment_data['slot']['slot_time'],
                "doctor": appointment_data['slot']['doctor_name'],
                "location": appointment_data['slot']['location'],
                "duration": appointment_data['slot']['duration_minutes']
            }
        )
        
    except ValueError as e:
        logger.error(f"❌ Booking error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/appointments/{booking_id}")
async def get_appointment(booking_id: str, db: aiosqlite.Connection = Depends(get_db)):
    """
    Get appointment details by booking ID
    
    **Path Parameters:**
    - `booking_id`: The unique booking ID (e.g., "A7F3B2C1")
    
    **Returns:**
    Complete appointment information including patient, doctor, and slot details
    
    **Raises:**
    - 404: Appointment not found
    """
    
    appointment = await get_appointment_by_booking_id(db, booking_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return appointment