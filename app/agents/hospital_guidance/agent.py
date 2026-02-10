from langgraph.graph import StateGraph, END
from typing import Dict, Any
import logging

from app.agents.hospital_guidance.nodes.routing_decision import llm_route_decision, route_request
from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage
from app.agents.hospital_guidance.nodes import (
    arrival,
    navigation,
    queue_management,
    visit_assistance,
    post_visit,
    emergency
)

logger = logging.getLogger(__name__)

def create_hospital_guidance_agent():
    """Create the main hospital guidance orchestrator"""
    
    workflow = StateGraph(HospitalGuidanceState)
    
    # ===== NODES =====
    
    # Entry point - routes based on intent
    workflow.add_node("route_request", route_request)
    
    # Arrival & Check-in
    workflow.add_node("handle_arrival", arrival.handle_arrival)
    workflow.add_node("initiate_check_in", arrival.initiate_check_in)
    workflow.add_node("complete_check_in", arrival.complete_check_in)
    
    # Navigation
    workflow.add_node("provide_navigation", navigation.provide_navigation)
    workflow.add_node("find_amenities", navigation.find_nearby_amenities)
    workflow.add_node("update_location", navigation.update_location)
    
    # Queue & Wait Management
    workflow.add_node("update_wait_time", queue_management.update_wait_time)
    workflow.add_node("suggest_activities", queue_management.suggest_activities_while_waiting)
    workflow.add_node("notify_family", queue_management.notify_family)
    
    # Visit Assistance
    workflow.add_node("start_visit", visit_assistance.start_visit)
    workflow.add_node("explain_term", visit_assistance.explain_medical_term)
    workflow.add_node("capture_notes", visit_assistance.capture_visit_notes)
    workflow.add_node("generate_questions", visit_assistance.generate_question_prompts)
    workflow.add_node("record_prescription", visit_assistance.record_prescription)
    workflow.add_node("record_test", visit_assistance.record_test_order)
    workflow.add_node("end_visit", visit_assistance.end_visit)
    
    # Post-Visit
    workflow.add_node("create_post_visit_tasks", post_visit.create_post_visit_tasks)
    workflow.add_node("handle_prescription", post_visit.handle_prescription_routing)
    workflow.add_node("schedule_lab", post_visit.schedule_lab_work)
    workflow.add_node("schedule_follow_up", post_visit.schedule_follow_up)
    workflow.add_node("process_payment", post_visit.process_payment)
    workflow.add_node("generate_discharge", post_visit.generate_discharge_instructions)
    workflow.add_node("initiate_departure", post_visit.initiate_departure)
    workflow.add_node("complete_journey", post_visit.complete_journey)
    
    # Emergency
    workflow.add_node("detect_emergency", emergency.detect_emergency)
    workflow.add_node("handle_emergency", emergency.handle_emergency)
    workflow.add_node("resolve_emergency", emergency.resolve_emergency)
    workflow.add_node("provide_support", emergency.provide_emotional_support)
    
    # ===== EDGES =====
    
    # Entry point
    workflow.set_entry_point("route_request")
    
    workflow.add_conditional_edges(
    "route_request",
    llm_route_decision,
    {
        "provide_navigation": "provide_navigation",
        "find_amenities": "find_amenities",
        "update_wait_time": "update_wait_time",
        "start_visit": "start_visit",
        "explain_term": "explain_term",
        "handle_arrival": "handle_arrival",
        "initiate_check_in": "initiate_check_in",
        "create_post_visit_tasks": "create_post_visit_tasks",
        "initiate_departure": "initiate_departure",
        "provide_support": "provide_support",
        "detect_emergency": "detect_emergency",
        "handle_emergency": "handle_emergency",
    }
)

    # All navigation nodes end
    workflow.add_edge("provide_navigation", END)
    workflow.add_edge("find_amenities", END)
    workflow.add_edge("update_location", END)
    
    # Wait/queue nodes end
    workflow.add_edge("update_wait_time", END)
    workflow.add_edge("suggest_activities", END)
    workflow.add_edge("notify_family", END)
    
    # Visit nodes end
    workflow.add_edge("start_visit", END)
    workflow.add_edge("explain_term", END)
    workflow.add_edge("capture_notes", END)
    workflow.add_edge("generate_questions", END)
    workflow.add_edge("record_prescription", END)
    workflow.add_edge("record_test", END)
    workflow.add_edge("end_visit", END)
    
    # Post-visit nodes end
    workflow.add_edge("create_post_visit_tasks", END)
    workflow.add_edge("handle_prescription", END)
    workflow.add_edge("schedule_lab", END)
    workflow.add_edge("schedule_follow_up", END)
    workflow.add_edge("process_payment", END)
    workflow.add_edge("generate_discharge", END)
    workflow.add_edge("initiate_departure", END)
    workflow.add_edge("complete_journey", END)
    
    # Emergency flow
    workflow.add_edge("detect_emergency", "handle_emergency")
    workflow.add_edge("handle_emergency", END)
    workflow.add_edge("resolve_emergency", END)
    workflow.add_edge("provide_support", END)
    
    # Arrival flow (for new journeys)
    workflow.add_edge("handle_arrival", END)
    workflow.add_edge("initiate_check_in", END)
    workflow.add_edge("complete_check_in", END)
    
    logger.info("Hospital guidance agent workflow compiled successfully")
    
    # return workflow.compile()

    graph = workflow.compile()

    mermaid = graph.get_graph().draw_mermaid()
    print(mermaid)

    return graph

# Create the agent
hospital_guidance_agent = create_hospital_guidance_agent()