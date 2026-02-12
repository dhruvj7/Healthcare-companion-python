
from app.agents.symptom_analysis.state import (
    SymptomAnalysisState, 
   
)
from typing import Dict, Any

from app.agents.doctor_finder.llm_helper import llm_resolve_specialty
from app.data.speciality import DISEASE_SPECIALTY_MAP
from app.agents.appointment_scheduler.crud import get_all_doctors
import aiosqlite
from pathlib import Path
import logging

from app.agents.appointment_scheduler.crud import get_available_slots_by_doctor_ids

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "database" / "appointments.db"


async def doctor_matching_node(state: SymptomAnalysisState):
    specialties = state.get("suggested_specialties", [])
    emergency = state.get("is_emergency", False)
    normalized_specialties = {normalize(s) for s in specialties}
    #fetching doctors from the database
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row  # Enable dict-like access
        doctors_list = await get_all_doctors(db)
    
    logger.info(f"Total doctors fetched: {len(doctors_list)}")

    logger.info(f"Doctor matching started")
    logger.info(f"Suggested specialties: {specialties}")
    logger.info(f"Emergency case: {emergency}")

    matched = [
        d for d in doctors_list
        if normalize(d["department"]) in normalized_specialties
        #and (not emergency or d["emergency_supported"])
    ]

    logger.info(f"Matched doctors count: {len(matched)}")

    return {
        **state,
        "matched_doctors": matched
    }





def normalize(value: str) -> str:
    return value.lower().strip()

def resolve_specialties(state: SymptomAnalysisState) -> Dict[str, Any]:
    diagnoses = state.get("differential_diagnosis") or []
    keywords = state.get("symptom_keywords") or []

    logger.info("Resolving medical specialty")
    logger.info(f"Diagnoses received: {diagnoses}")
    logger.info(f"Symptom keywords received: {keywords}")

    # ---------------- 1. RULE-BASED RESOLUTION FIRST ----------------
    rule_specialties = set()

    for text in diagnoses + keywords:
        text_lower = text.lower()
        for disease, specialty in DISEASE_SPECIALTY_MAP.items():
            if disease.lower() in text_lower:
                rule_specialties.add(specialty)

    logger.info(f"Rule-based specialties found: {list(rule_specialties)}")

    if rule_specialties:
        final_specialty = list(rule_specialties)[0]
        decision_reason = "Rule-based (LLM skipped)"

        logger.info(f"Final specialty selected: {final_specialty}")
        logger.info(f"Decision reason: {decision_reason}")

        return {
            **state,
            "suggested_specialties": [final_specialty],
        }

    # ---------------- 2. LLM FALLBACK ONLY ----------------
    combined_text = ", ".join(diagnoses + keywords)
    logger.info(f"Combined text for LLM: {combined_text}")

    try:
        llm_specialty = llm_resolve_specialty(combined_text)
        logger.info(f"LLM predicted specialty: {llm_specialty}")
    except Exception as e:
        logger.warning(f"LLM specialty resolution failed: {e}")
        llm_specialty = None

    if llm_specialty:
        final_specialty = llm_specialty
        decision_reason = "LLM fallback"
    else:
        final_specialty = "General Medicine"
        decision_reason = "Safe default fallback"

    logger.info(f"Final specialty selected: {final_specialty}")
    logger.info(f"Decision reason: {decision_reason}")

    return {
        **state,
        "suggested_specialties": [final_specialty],
    }

async def get_available_appointments_node(state: SymptomAnalysisState):
    matched_doctors = state.get("matched_doctors", [])
    doctor_ids = [d["id"] for d in matched_doctors]

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row  # Enable dict-like access
        available_slots = await get_available_slots_by_doctor_ids(db, doctor_ids)

    # Group slots by doctor_id
    grouped_slots = {}
    for slot in available_slots:
        doctor_id = slot["doctor_id"]
        if doctor_id not in grouped_slots:
            grouped_slots[doctor_id] = []
        grouped_slots[doctor_id].append(slot)

    logger.info(f"Available appointments fetched for {len(grouped_slots)} doctors")
    logger.info(f"Doctor IDs with available slots: {list(grouped_slots.keys())}")

    return {
        **state,
        "available_appointments": grouped_slots
    }
