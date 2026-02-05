# agents/appointment_scheduler/models.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, time

class DoctorResponse(BaseModel):
    """Response model for doctor information"""
    id: int
    name: str
    email: str
    specialty: Optional[str]

class AvailableSlotResponse(BaseModel):
    """Response model for available appointment slots"""
    id: int
    doctor_id: int
    doctor_name: str
    doctor_specialty: Optional[str]
    slot_date: str
    slot_time: str
    duration_minutes: int
    location: str

class BookingRequest(BaseModel):
    """Request model for booking an appointment"""
    slot_id: int
    patient_name: str
    patient_email: EmailStr
    patient_phone: str
    reason_for_visit: str
    appointment_type: str = "in-person"  # or "telemedicine"
    
    class Config:
        json_schema_extra = {
            "example": {
                "slot_id": 1,
                "patient_name": "John Doe",
                "patient_email": "john.doe@example.com",
                "patient_phone": "555-0123",
                "reason_for_visit": "Annual checkup",
                "appointment_type": "in-person"
            }
        }

class BookingResponse(BaseModel):
    """Response model for successful booking"""
    booking_id: str
    status: str
    message: str
    appointment_details: dict
    
    class Config:
        json_schema_extra = {
            "example": {
                "booking_id": "A7F3B2C1",
                "status": "confirmed",
                "message": "Appointment booked successfully!",
                "appointment_details": {
                    "date": "2026-02-10",
                    "time": "14:00",
                    "doctor": "Dr. Sarah Smith",
                    "location": "Clinic Room 1",
                    "duration": 30
                }
            }
        }