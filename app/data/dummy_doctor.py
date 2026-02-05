import random
import uuid

SPECIALTIES = [
    "Cardiology",
    "Neurology",
    "Pulmonology",
    "Orthopedics",
    "Dermatology",
    "Gastroenterology",
    "Endocrinology",
    "General Medicine"
]

HOSPITALS = [
    "CityCare Hospital",
    "Apollo Clinic",
    "Fortis Health",
    "Max Healthcare",
    "AIIMS Partner Clinic"
]

CITIES = [
    ("Delhi", 28.61, 77.20),
    ("Mumbai", 19.07, 72.87),
    ("Bangalore", 12.97, 77.59),
    ("Pune", 18.52, 73.85),
    ("Hyderabad", 17.38, 78.48)
]

def generate_doctors(n=120):
    doctors = []
    for _ in range(n):
        city, lat, lon = random.choice(CITIES)
        specialty = random.choice(SPECIALTIES)

        doctors.append({
            "id": str(uuid.uuid4()),
            "name": f"Dr. {random.choice(['A', 'R', 'S', 'M'])}. {random.choice(['Sharma', 'Verma', 'Mehta', 'Iyer'])}",
            "specialty": specialty,
            "hospital": random.choice(HOSPITALS),
            "city": city,
            "lat": lat + random.uniform(-0.05, 0.05),
            "lon": lon + random.uniform(-0.05, 0.05),
            "emergency_supported": specialty in ["Cardiology", "Neurology", "Pulmonology"],
            "available_slots": random.sample(
                ["09:00", "11:00", "14:00", "16:00", "18:00"], k=3
            ),
            "accepts_insurance": random.choice([True, False])
        })
    return doctors

DOCTORS_DB = generate_doctors()
