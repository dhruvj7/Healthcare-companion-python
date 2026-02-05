
from app.agents.symptom_analysis.state import (
    SymptomAnalysisState, 
   
)

def doctor_matching_node(state: SymptomAnalysisState):
    specialties = state["suggested_specialties"]
    emergency = state.get("is_emergency", False)

    DOCTORS_DB = [
        {
            "name": "Dr. A. Sharma",
            "specialty": "Cardiology",
            "hospital": "City Heart Hospital",
            "emergency_supported": True
        },
        {
            "name": "Dr. R. Mehta",
            "specialty": "General Medicine",
            "hospital": "CarePlus Clinic",
            "emergency_supported": False
        },
          {
            "name": "Dr. Rm sharma",
            "specialty": "Neurology",
            "hospital": "CarePlus Clinic",
            "emergency_supported": False
        }
    ]

    matched = [
        d for d in DOCTORS_DB
        if d["specialty"] in specialties
        and (not emergency or d["emergency_supported"])
    ]

    return {
        **state,
        "matched_doctors": matched
    }
DIAGNOSIS_TO_SPECIALTY = {
    "heart attack": "Cardiology",
    "chest pain": "Cardiology",
    "asthma": "Pulmonology",
    "pneumonia": "Pulmonology",
    "migraine": "Neurology",
    "stroke": "Neurology",
    "fever": "General Medicine"
}

def resolve_specialties(state: SymptomAnalysisState):
    diagnoses = state.get("differential_diagnosis") or []
    keywords = state.get("symptom_keywords") or []

    specialties = set()

    for d in diagnoses + keywords:
        d_lower = d.lower()
        for k, v in DIAGNOSIS_TO_SPECIALTY.items():
            if k in d_lower:
                specialties.add(v)

    if not specialties:
        specialties.add("General Medicine")

    return {
        **state,
        "suggested_specialties": list(specialties)
    }

