from langgraph.graph import StateGraph, END
import logging

from app.agents.symptom_analysis.state import SymptomAnalysisState
from app.agents.symptom_analysis.nodes import (
    determine_age_group,
    extract_symptom_keywords,
    check_emergency_conditions,
    analyze_symptoms_with_llm,
    finalize_recommendations
)

logger = logging.getLogger(__name__)

def create_symptom_analysis_workflow():
    """Create and compile the symptom analysis LangGraph workflow"""
    
    workflow = StateGraph(SymptomAnalysisState)
    
    # Add nodes
    workflow.add_node("determine_age", determine_age_group)
    workflow.add_node("extract_keywords", extract_symptom_keywords)
    workflow.add_node("check_emergency", check_emergency_conditions)
    workflow.add_node("analyze_llm", analyze_symptoms_with_llm)
    workflow.add_node("finalize", finalize_recommendations)
    
    # Define flow
    workflow.set_entry_point("determine_age")
    workflow.add_edge("determine_age", "extract_keywords")
    workflow.add_edge("extract_keywords", "check_emergency")
    
    # Conditional routing
    def should_analyze(state):
        return "skip" if state.get('is_emergency') else "analyze"
    
    workflow.add_conditional_edges(
        "check_emergency",
        should_analyze,
        {
            "analyze": "analyze_llm",
            "skip": "finalize"
        }
    )
    
    workflow.add_edge("analyze_llm", "finalize")
    workflow.add_edge("finalize", END)
    
    logger.info("Symptom analysis workflow compiled successfully")
    graph = workflow.compile()

    mermaid = graph.get_graph().draw_mermaid()
    print(mermaid)

    return graph

# Global workflow instance
symptom_agent = create_symptom_analysis_workflow()