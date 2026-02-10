from langgraph.graph import StateGraph, END
from app.agents.symptom_analysis.state import SymptomAnalysisState
from app.agents.doctor_finder.node import (
    resolve_specialties,
    doctor_matching_node,
    get_available_appointments_node
)

def create_doctor_finder_workflow():
    workflow = StateGraph(SymptomAnalysisState)

    workflow.add_node("resolve_specialty", resolve_specialties)
    workflow.add_node("match_doctors", doctor_matching_node)
    workflow.add_node("available_slots", get_available_appointments_node)

    workflow.set_entry_point("resolve_specialty")
    workflow.add_edge("resolve_specialty", "match_doctors")
    workflow.add_edge("match_doctors", "available_slots")
    workflow.add_edge("available_slots", END)

    return workflow.compile()




doctor_agent = create_doctor_finder_workflow()
