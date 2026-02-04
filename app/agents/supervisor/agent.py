# from app.agents.symptom_analysis.workflow import symptom_agent
from app.agents.doctor_finder.agent import doctor_agent
from app.agents.symptom_analysis.agent import symptom_agent;

def run_patient_journey(initial_state):
    # Step 1: Symptom analysis
    state_after_symptoms = symptom_agent.invoke(initial_state)

    # Step 2: Decide if doctor agent is needed
    if state_after_symptoms.get("requires_doctor"):
        state_after_doctor = doctor_agent.invoke(state_after_symptoms)
        return state_after_doctor

    return state_after_symptoms
