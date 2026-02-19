# app/crud.py
import aiosqlite
from typing import List, Optional
import uuid
from datetime import datetime

async def get_all_doctors(
    db: aiosqlite.Connection,
    city: Optional[str] = None,
    region: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: Optional[float] = None
) -> List[dict]:
    """Get all doctors, optionally filtered by location"""
    query = """
        SELECT id, name, email, specialty, department, city, region, latitude, longitude, ambulance_phone
        FROM doctors
        WHERE 1=1
    """
    params = []
    
    # Filter by city
    if city:
        query += " AND LOWER(city) = LOWER(?)"
        params.append(city)
    
    # Filter by region
    if region:
        query += " AND LOWER(region) = LOWER(?)"
        params.append(region)
    
    # Filter by proximity (simple distance calculation)
    if latitude and longitude and radius_km:
        # Using simple bounding box approximation (1 degree ≈ 111 km)
        lat_range = radius_km / 111.0
        lon_range = radius_km / (111.0 * abs(latitude / 90.0) if latitude != 0 else 1)
        query += " AND latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?"
        params.extend([latitude - lat_range, latitude + lat_range, longitude - lon_range, longitude + lon_range])
    
    query += " ORDER BY name"
    
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    doctors = [dict(row) for row in rows]
    
    # If proximity filtering, calculate actual distance and filter
    if latitude and longitude and radius_km:
        import math
        filtered_doctors = []
        for doctor in doctors:
            if doctor.get('latitude') and doctor.get('longitude'):
                # Haversine formula for distance
                lat1, lon1 = math.radians(latitude), math.radians(longitude)
                lat2, lon2 = math.radians(doctor['latitude']), math.radians(doctor['longitude'])
                dlat, dlon = lat2 - lat1, lon2 - lon1
                a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
                c = 2 * math.asin(math.sqrt(a))
                distance_km = 6371 * c  # Earth radius in km
                if distance_km <= radius_km:
                    doctor['distance_km'] = round(distance_km, 2)
                    filtered_doctors.append(doctor)
        # Sort by distance
        filtered_doctors.sort(key=lambda x: x.get('distance_km', float('inf')))
        return filtered_doctors
    
    return doctors


async def get_doctors_by_specialty(
    db: aiosqlite.Connection,
    specialty: str,
    limit: Optional[int] = 5,
    city: Optional[str] = None,
    region: Optional[str] = None,
) -> List[dict]:
    """Get doctors by specialty (matches specialty or department), with optional limit and location."""
    # Normalize: match both "Cardiologist" (specialty) and "Cardiology" (department) in DB
    specialty_clean = specialty.strip().lower()
    if specialty_clean.endswith("ist"):
        term_ology = specialty_clean[:-2] + "y"
        term_ist = specialty_clean
    else:
        term_ology = specialty_clean
        term_ist = (specialty_clean[:-1] + "ist") if specialty_clean.endswith("y") else (specialty_clean + "ist")
    query = """
        SELECT id, name, email, specialty, department, city, region, latitude, longitude, ambulance_phone
        FROM doctors
        WHERE LOWER(specialty) LIKE ? OR LOWER(department) LIKE ? OR LOWER(specialty) LIKE ? OR LOWER(department) LIKE ?
    """
    params = [f"%{term_ist}%", f"%{term_ology}%", f"%{term_ology}%", f"%{term_ist}%"]
    if city:
        query += " AND LOWER(city) = LOWER(?)"
        params.append(city)
    if region:
        query += " AND LOWER(region) = LOWER(?)"
        params.append(region)
    query += " ORDER BY name LIMIT ?"
    params.append(limit if limit else 20)
    cursor = await db.execute(query, params)
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

async def get_available_slots_by_doctor_ids(db: aiosqlite.Connection, doctor_ids: list) -> List[dict]:
    """Get available slots for a list of doctor IDs"""
    if not doctor_ids:
        return []
    
    placeholders = ','.join('?' for _ in doctor_ids)
    query = f"""
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
        WHERE s.is_booked = 0 AND s.doctor_id IN ({placeholders})
        ORDER BY s.slot_date, s.slot_time
    """
    
    cursor = await db.execute(query, doctor_ids)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]