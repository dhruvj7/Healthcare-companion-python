from typing import Dict, Any, List
import logging
from datetime import datetime

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

def start_visit(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Mark visit as started and provide pre-visit reminders"""
    
    logger.info(f"Visit started for patient {state['patient_id']} with {state['doctor_name']}")
    
    # Generate pre-visit reminders
    llm = get_llm()
    reminder_prompt = f"""
    Generate brief pre-visit reminders for a patient about to see the doctor.
    
    Patient info:
    - Reason for visit: {state['reason_for_visit']}
    - Doctor: {state['doctor_name']}
    
    Include:
    1. Reminder about why they're here
    2. Suggestion to mention any new symptoms
    3. Encouragement to ask questions
    
    Keep it brief (3-4 sentences), supportive, and actionable.
    """
    
    try:
        reminder_response = llm.invoke(reminder_prompt)
        reminders = reminder_response.content
    except Exception as e:
        logger.error(f"Error generating reminders: {e}")
        reminders = f"You're seeing Dr. {state['doctor_name']} for {state['reason_for_visit']}. Don't forget to mention any new symptoms and ask any questions you have."
    
    # Remove from queue
    from app.agents.hospital_guidance.tools.queue_tool import queue_tool
    doctor_id = f"dr_{state['doctor_name'].lower().replace(' ', '_')}"
    queue_tool.remove_from_queue(state['patient_id'], doctor_id)
    
    notification = {
        "type": "info",
        "title": "Visit Starting",
        "message": reminders,
        "timestamp": datetime.now()
    }
    
    return {
        **state,
        "journey_stage": JourneyStage.IN_VISIT,
        "visit_started": True,
        "queue_position": None,
        "estimated_wait_time": None,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def explain_medical_term(state: HospitalGuidanceState, term: str) -> Dict[str, Any]:
    """Explain medical terminology in simple language"""
    
    logger.info(f"Explaining medical term: {term}")
    
    llm = get_llm()
    explanation_prompt = f"""
    Explain this medical term in simple, patient-friendly language:
    
    Term: {term}
    
    Guidelines:
    - Use everyday language (5th-grade reading level)
    - Keep it brief (2-3 sentences)
    - Include what it means for the patient
    - Avoid technical jargon
    
    Example format:
    "[Term] means [simple explanation]. In your case, this relates to [patient context]."
    """
    
    try:
        explanation_response = llm.invoke(explanation_prompt)
        explanation = explanation_response.content
    except Exception as e:
        logger.error(f"Error explaining term: {e}")
        explanation = f"I'll help you understand '{term}' - let me look that up for you."
    
    # Add to conversation history
    conversation_entry = {
        "timestamp": datetime.now(),
        "query": f"What does '{term}' mean?",
        "response": explanation,
        "type": "medical_explanation"
    }
    
    return {
        **state,
        "conversation_history": state.get("conversation_history", []) + [conversation_entry],
        "notifications": state.get("notifications", []) + [{
            "type": "info",
            "title": f"Medical Term: {term}",
            "message": explanation,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def capture_visit_notes(state: HospitalGuidanceState, notes: str) -> Dict[str, Any]:
    """Capture important points from the visit"""
    
    logger.info(f"Capturing visit notes for patient {state['patient_id']}")
    
    # Use LLM to structure the notes
    llm = get_llm()
    structuring_prompt = f"""
    Structure these visit notes into a clear, organized format.
    
    Notes: {notes}
    
    Organize into sections:
    - Key Findings
    - Diagnosis/Assessment
    - Treatment Plan
    - Next Steps
    
    Keep it concise and patient-friendly.
    """
    
    try:
        structured_response = llm.invoke(structuring_prompt)
        structured_notes = structured_response.content
    except Exception as e:
        logger.error(f"Error structuring notes: {e}")
        structured_notes = notes
    
    conversation_entry = {
        "timestamp": datetime.now(),
        "type": "visit_notes",
        "content": structured_notes
    }
    
    return {
        **state,
        "visit_summary": structured_notes,
        "conversation_history": state.get("conversation_history", []) + [conversation_entry],
        "last_updated": datetime.now()
    }


def generate_question_prompts(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Suggest questions patient should ask doctor"""
    
    logger.info("Generating question suggestions")
    
    llm = get_llm()
    questions_prompt = f"""
    Generate 3-5 important questions a patient should ask their doctor.
    
    Patient context:
    - Visiting: {state['doctor_name']}
    - Reason: {state['reason_for_visit']}
    - Department: {state.get('department', 'General')}
    
    Focus on:
    - Treatment options and side effects
    - Recovery timeline and expectations
    - Follow-up care
    - Lifestyle modifications
    - When to seek urgent care
    
    Format as a numbered list. Keep questions clear and actionable.
    """
    
    try:
        questions_response = llm.invoke(questions_prompt)
        questions = questions_response.content
    except Exception as e:
        logger.error(f"Error generating questions: {e}")
        questions = """
        1. What are my treatment options?
        2. Are there any side effects I should watch for?
        3. When should I schedule a follow-up?
        4. What lifestyle changes should I make?
        5. When should I seek urgent care?
        """
    
    return {
        **state,
        "notifications": state.get("notifications", []) + [{
            "type": "info",
            "title": "Questions to Ask Your Doctor",
            "message": questions,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def record_prescription(
    state: HospitalGuidanceState, 
    medication: str,
    dosage: str,
    frequency: str,
    instructions: str
) -> Dict[str, Any]:
    """Record prescription information"""
    
    prescription = {
        "medication": medication,
        "dosage": dosage,
        "frequency": frequency,
        "instructions": instructions,
        "prescribed_at": datetime.now(),
        "prescribed_by": state['doctor_name']
    }
    
    prescriptions = state.get("prescriptions", [])
    prescriptions.append(prescription)
    
    logger.info(f"Recorded prescription: {medication} for patient {state['patient_id']}")
    
    # Generate patient-friendly explanation
    llm = get_llm()
    explanation_prompt = f"""
    Explain this prescription in simple, patient-friendly language:
    
    Medication: {medication}
    Dosage: {dosage}
    Frequency: {frequency}
    Instructions: {instructions}
    
    Include:
    - What the medication does
    - How to take it
    - Important reminders
    
    Keep it brief (3-4 sentences) and reassuring.
    """
    
    try:
        explanation_response = llm.invoke(explanation_prompt)
        explanation = explanation_response.content
    except Exception as e:
        logger.error(f"Error explaining prescription: {e}")
        explanation = f"Take {medication} {dosage} {frequency}. {instructions}"
    
    return {
        **state,
        "prescriptions": prescriptions,
        "notifications": state.get("notifications", []) + [{
            "type": "prescription",
            "title": f"New Prescription: {medication}",
            "message": explanation,
            "prescription": prescription,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def record_test_order(
    state: HospitalGuidanceState,
    test_name: str,
    test_type: str,
    urgency: str,
    instructions: str
) -> Dict[str, Any]:
    """Record ordered tests (lab work, imaging, etc.)"""
    
    test_order = {
        "test_name": test_name,
        "test_type": test_type,  # lab, imaging, etc.
        "urgency": urgency,  # routine, urgent, stat
        "instructions": instructions,
        "ordered_at": datetime.now(),
        "ordered_by": state['doctor_name'],
        "completed": False
    }
    
    tests_ordered = state.get("tests_ordered", [])
    tests_ordered.append(test_order)
    
    logger.info(f"Recorded test order: {test_name} for patient {state['patient_id']}")
    
    return {
        **state,
        "tests_ordered": tests_ordered,
        "notifications": state.get("notifications", []) + [{
            "type": "test_order",
            "title": f"Test Ordered: {test_name}",
            "message": f"Dr. {state['doctor_name']} ordered {test_name}. {instructions}",
            "test_order": test_order,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def end_visit(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Mark visit as complete and generate summary"""
    
    logger.info(f"Visit ended for patient {state['patient_id']}")
    
    # Generate comprehensive visit summary
    llm = get_llm()
    summary_prompt = f"""
    Generate a comprehensive visit summary for the patient.
    
    Visit details:
    - Doctor: {state['doctor_name']}
    - Reason: {state['reason_for_visit']}
    - Diagnosis: {state.get('diagnosis', 'Not specified')}
    - Prescriptions: {len(state.get('prescriptions', []))} medications
    - Tests ordered: {len(state.get('tests_ordered', []))} tests
    - Follow-up needed: {state.get('follow_up_needed', False)}
    
    Visit notes: {state.get('visit_summary', 'No notes available')}
    
    Create a clear, organized summary with sections:
    1. What We Discussed
    2. Diagnosis/Findings
    3. Treatment Plan
    4. Next Steps
    
    Make it patient-friendly and actionable.
    """
    
    try:
        summary_response = llm.invoke(summary_prompt)
        final_summary = summary_response.content
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        final_summary = f"Visit with Dr. {state['doctor_name']} completed. Please see your after-visit summary for details."
    
    return {
        **state,
        "journey_stage": JourneyStage.POST_VISIT,
        "visit_ended": True,
        "visit_summary": final_summary,
        "notifications": state.get("notifications", []) + [{
            "type": "success",
            "title": "Visit Complete",
            "message": final_summary,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }