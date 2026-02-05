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
                email TEXT NOT NULL UNIQUE,
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
        
        # Insert sample doctors
        await db.execute("""
            INSERT INTO doctors (name, email, specialty)
            VALUES 
                ('Dr. Sarah Smith', 'khushaal.sharma@veersatech.com', 'General Practitioner'),
                ('Dr. John Davis', 'khushaalsharma1@gmail.com', 'Cardiologist'),
                ('Dr. Emily Chen', 'khushaalsharma12drosary@gmail.com', 'Pediatrician')
        """)
        
        # Insert available slots for Dr. Smith (ID=1)
        await db.executemany("""
            INSERT INTO available_slots (doctor_id, slot_date, slot_time, duration_minutes, location)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (1, '2026-02-10', '09:00', 30, 'Clinic Room 1'),
            (1, '2026-02-10', '10:00', 30, 'Clinic Room 1'),
            (1, '2026-02-10', '11:00', 30, 'Clinic Room 1'),
            (1, '2026-02-10', '14:00', 30, 'Clinic Room 1'),
            (1, '2026-02-10', '15:00', 30, 'Clinic Room 1'),
            (1, '2026-02-12', '09:00', 30, 'Clinic Room 1'),
            (1, '2026-02-12', '10:30', 30, 'Clinic Room 1'),
            (1, '2026-02-12', '14:00', 30, 'Clinic Room 1'),
            (1, '2026-02-12', '15:30', 30, 'Clinic Room 1'),
        ])
        
        # Insert slots for Dr. Davis (ID=2)
        await db.executemany("""
            INSERT INTO available_slots (doctor_id, slot_date, slot_time, duration_minutes, location)
            VALUES (?, ?, ?, ?, ?)
        """, [
            (2, '2026-02-11', '10:00', 45, 'Cardiology Wing - Room 5'),
            (2, '2026-02-11', '11:00', 45, 'Cardiology Wing - Room 5'),
            (2, '2026-02-11', '14:00', 45, 'Cardiology Wing - Room 5'),
            (2, '2026-02-13', '09:00', 45, 'Cardiology Wing - Room 5'),
            (2, '2026-02-13', '10:00', 45, 'Cardiology Wing - Room 5'),
        ])
        
        await db.commit()
        print("✅ Sample data seeded successfully")