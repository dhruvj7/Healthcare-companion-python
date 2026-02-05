# app/crud.py
import aiosqlite
from typing import List, Optional
import uuid
from datetime import datetime

async def get_all_doctors(db: aiosqlite.Connection) -> List[dict]:
    """Get all doctors"""
    cursor = await db.execute("""
        SELECT id, name, email, specialty
        FROM doctors
        ORDER BY name
    """)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_available_slots(
    db: aiosqlite.Connection, 
    doctor_id: Optional[int] = None
) -> List[dict]:
    """Get all available (unbooked) slots, optionally filtered by doctor"""
    
    query = """
        SELECT 
            s.id,
            s.doctor_id,
            d.name as doctor_name,
            d.specialty as doctor_specialty,
            s.slot_date,
            s.slot_time,
            s.duration_minutes,
            s.location
        FROM available_slots s
        JOIN doctors d ON s.doctor_id = d.id
        WHERE s.is_booked = 0
    """
    
    params = []
    if doctor_id:
        query += " AND s.doctor_id = ?"
        params.append(doctor_id)
    
    query += " ORDER BY s.slot_date, s.slot_time"
    
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_slot_details(db: aiosqlite.Connection, slot_id: int) -> Optional[dict]:
    """Get details of a specific slot"""
    cursor = await db.execute("""
        SELECT 
            s.id,
            s.doctor_id,
            d.name as doctor_name,
            d.email as doctor_email,
            d.specialty as doctor_specialty,
            s.slot_date,
            s.slot_time,
            s.duration_minutes,
            s.location,
            s.is_booked
        FROM available_slots s
        JOIN doctors d ON s.doctor_id = d.id
        WHERE s.id = ?
    """, (slot_id,))
    
    row = await cursor.fetchone()
    return dict(row) if row else None


async def book_appointment(
    db: aiosqlite.Connection,
    slot_id: int,
    patient_name: str,
    patient_email: str,
    patient_phone: str,
    reason_for_visit: str,
    appointment_type: str
) -> dict:
    """Book an appointment"""
    
    # Check if slot is still available
    slot = await get_slot_details(db, slot_id)
    
    if not slot:
        raise ValueError("Slot not found")
    
    if slot['is_booked']:
        raise ValueError("Slot is already booked")
    
    # Generate unique booking ID
    booking_id = str(uuid.uuid4())[:8].upper()
    
    # Create appointment
    await db.execute("""
        INSERT INTO appointments 
        (slot_id, patient_name, patient_email, patient_phone, reason_for_visit, appointment_type, booking_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (slot_id, patient_name, patient_email, patient_phone, reason_for_visit, appointment_type, booking_id))
    
    # Mark slot as booked
    await db.execute("""
        UPDATE available_slots
        SET is_booked = 1
        WHERE id = ?
    """, (slot_id,))
    
    await db.commit()
    
    return {
        "booking_id": booking_id,
        "slot": slot,
        "patient_name": patient_name,
        "patient_email": patient_email,
        "patient_phone": patient_phone,
        "reason_for_visit": reason_for_visit,
        "appointment_type": appointment_type
    }


async def get_appointment_by_booking_id(db: aiosqlite.Connection, booking_id: str) -> Optional[dict]:
    """Get appointment details by booking ID"""
    cursor = await db.execute("""
        SELECT 
            a.*,
            s.slot_date,
            s.slot_time,
            s.duration_minutes,
            s.location,
            d.name as doctor_name,
            d.email as doctor_email,
            d.specialty as doctor_specialty
        FROM appointments a
        JOIN available_slots s ON a.slot_id = s.id
        JOIN doctors d ON s.doctor_id = d.id
        WHERE a.booking_id = ?
    """, (booking_id,))
    
    row = await cursor.fetchone()
    return dict(row) if row else None