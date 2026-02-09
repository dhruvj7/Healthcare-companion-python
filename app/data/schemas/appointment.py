import aiosqlite
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "database" / "appointments.db"


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Initializing database at {DB_PATH}...")

    async with aiosqlite.connect(DB_PATH) as db:
        # Doctors table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                specialty TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Available slots table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS available_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doctor_id INTEGER NOT NULL,
                slot_date DATE NOT NULL,
                slot_time TIME NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                location TEXT,
                is_booked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id)
            )
        """)
        
        # Appointments table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_id INTEGER NOT NULL,
                patient_name TEXT NOT NULL,
                patient_email TEXT NOT NULL,
                patient_phone TEXT,
                reason_for_visit TEXT,
                appointment_type TEXT DEFAULT 'in-person',
                status TEXT DEFAULT 'confirmed',
                booking_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (slot_id) REFERENCES available_slots(id)
            )
        """)
        
        await db.commit()
        print("✅ Database initialized successfully")


async def get_db_connection():
    """
    Get database connection - creates a NEW connection each time
    
    Usage:
        async with get_db() as db:  # NOT: async with await get_db()
            # use db
    """
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()

async def seed_sample_data():
    """Add sample doctors and available slots for testing"""
    
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if data already exists
        cursor = await db.execute("SELECT COUNT(*) FROM doctors")
        count = await cursor.fetchone()
        
        if count[0] > 0:
            print("Sample data already exists")
            return
        
        # Insert 25 sample doctors with various specialties
        doctors = [
            ('Dr. Sarah Smith', 'khushaal.sharma@veersatech.com', 'General Practitioner'),
            ('Dr. John Davis', 'khushaal.sharma@veersatech.com', 'Cardiologist'),
            ('Dr. Emily Chen', 'khushaal.sharma@veersatech.com', 'Pediatrician'),
            ('Dr. Michael Brown', 'khushaal.sharma@veersatech.com', 'General Practitioner'),
            ('Dr. Jessica Wilson', 'khushaal.sharma@veersatech.com', 'Dermatologist'),
            ('Dr. David Martinez', 'khushaal.sharma@veersatech.com', 'Cardiologist'),
            ('Dr. Lisa Anderson', 'khushaal.sharma@veersatech.com', 'Pediatrician'),
            ('Dr. Robert Taylor', 'khushaal.sharma@veersatech.com', 'Orthopedic Surgeon'),
            ('Dr. Maria Garcia', 'khushaal.sharma@veersatech.com', 'General Practitioner'),
            ('Dr. James Thompson', 'khushaal.sharma@veersatech.com', 'Neurologist'),
            ('Dr. Jennifer Lee', 'khushaal.sharma@veersatech.com', 'Dermatologist'),
            ('Dr. William Harris', 'khushaal.sharma@veersatech.com', 'Cardiologist'),
            ('Dr. Amanda Clark', 'khushaal.sharma@veersatech.com', 'Pediatrician'),
            ('Dr. Christopher Lewis', 'khushaal.sharma@veersatech.com', 'Orthopedic Surgeon'),
            ('Dr. Michelle Walker', 'khushaal.sharma@veersatech.com', 'Psychiatrist'),
            ('Dr. Daniel Hall', 'khushaal.sharma@veersatech.com', 'General Practitioner'),
            ('Dr. Rebecca Allen', 'khushaal.sharma@veersatech.com', 'Ophthalmologist'),
            ('Dr. Kevin Young', 'khushaal.sharma@veersatech.com', 'Neurologist'),
            ('Dr. Laura King', 'khushaal.sharma@veersatech.com', 'Dermatologist'),
            ('Dr. Brian Wright', 'khushaal.sharma@veersatech.com', 'Cardiologist'),
            ('Dr. Stephanie Scott', 'khushaal.sharma@veersatech.com', 'Pediatrician'),
            ('Dr. Anthony Green', 'khushaal.sharma@veersatech.com', 'Orthopedic Surgeon'),
            ('Dr. Nicole Adams', 'khushaal.sharma@veersatech.com', 'Psychiatrist'),
            ('Dr. Matthew Baker', 'khushaal.sharma@veersatech.com', 'General Practitioner'),
            ('Dr. Elizabeth Nelson', 'khushaal.sharma@veersatech.com', 'Ophthalmologist'),
        ]
        
        await db.executemany("""
            INSERT INTO doctors (name, email, specialty)
            VALUES (?, ?, ?)
        """, doctors)
        
        # Generate slots for each doctor (doctor_id 1-25)
        all_slots = []
        
        for doctor_id in range(1, 26):
            # Determine duration and location based on specialty
            if doctor_id in [2, 6, 12, 20]:  # Cardiologists
                duration = 45
                location = f'Cardiology Wing - Room {doctor_id}'
            elif doctor_id in [3, 7, 13, 21]:  # Pediatricians
                duration = 30
                location = f'Pediatrics - Room {doctor_id}'
            elif doctor_id in [8, 14, 22]:  # Orthopedic Surgeons
                duration = 60
                location = f'Orthopedics - Room {doctor_id}'
            elif doctor_id in [10, 18]:  # Neurologists
                duration = 45
                location = f'Neurology - Room {doctor_id}'
            elif doctor_id in [5, 11, 19]:  # Dermatologists
                duration = 30
                location = f'Dermatology - Room {doctor_id}'
            elif doctor_id in [15, 23]:  # Psychiatrists
                duration = 60
                location = f'Psychiatry - Room {doctor_id}'
            elif doctor_id in [17, 25]:  # Ophthalmologists
                duration = 30
                location = f'Ophthalmology - Room {doctor_id}'
            else:  # General Practitioners
                duration = 30
                location = f'Clinic Room {doctor_id}'
            
            # Create at least 7 slots per doctor across multiple dates
            base_date = 10 + (doctor_id % 5)  # Distribute across Feb 10-14
            
            slots_for_doctor = [
                (doctor_id, f'2026-02-{base_date:02d}', '09:00', duration, location),
                (doctor_id, f'2026-02-{base_date:02d}', '10:00', duration, location),
                (doctor_id, f'2026-02-{base_date:02d}', '11:00', duration, location),
                (doctor_id, f'2026-02-{base_date:02d}', '14:00', duration, location),
                (doctor_id, f'2026-02-{base_date:02d}', '15:00', duration, location),
                (doctor_id, f'2026-02-{(base_date + 2):02d}', '09:00', duration, location),
                (doctor_id, f'2026-02-{(base_date + 2):02d}', '10:30', duration, location),
                (doctor_id, f'2026-02-{(base_date + 2):02d}', '14:00', duration, location),
            ]
            
            all_slots.extend(slots_for_doctor)
        
        # Insert all slots at once
        await db.executemany("""
            INSERT INTO available_slots (doctor_id, slot_date, slot_time, duration_minutes, location)
            VALUES (?, ?, ?, ?, ?)
        """, all_slots)
        
        await db.commit()
        print(f"Successfully seeded {len(doctors)} doctors with {len(all_slots)} available slots")