# app/agents/hospital_guidance/agent.py
from langgraph.graph import StateGraph, END
from typing import Dict, Any
import logging

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
    
    # Arrival & Check-in
    workflow.add_node("handle_arrival", arrival.handle_arrival)
    workflow.add_node("initiate_check_in", arrival.initiate_check_in)
    workflow.add_node("complete_check_in", arrival.complete_check_in)
    
    # Navigation
    workflow.add_node("provide_navigation", lambda state: navigation.provide_navigation(state, state.get("navigation_query", "")))
    workflow.add_node("find_amenities", navigation.find_nearby_amenities)
    workflow.add_node("update_location", lambda state: navigation.update_location(state, state.get("new_location", {})))
    
    # Queue & Wait Management
    workflow.add_node("update_wait_time", queue_management.update_wait_time)
    workflow.add_node("suggest_activities", queue_management.suggest_activities_while_waiting)
    workflow.add_node("notify_family", lambda state: queue_management.notify_family(state, state.get("family_message", "")))
    
    # Visit Assistance
    workflow.add_node("start_visit", visit_assistance.start_visit)
    workflow.add_node("explain_term", lambda state: visit_assistance.explain_medical_term(state, state.get("medical_term", "")))
    workflow.add_node("capture_notes", lambda state: visit_assistance.capture_visit_notes(state, state.get("visit_notes", "")))
    workflow.add_node("generate_questions", visit_assistance.generate_question_prompts)
    workflow.add_node("record_prescription", lambda state: visit_assistance.record_prescription(
        state,
        state.get("medication", ""),
        state.get("dosage", ""),
        state.get("frequency", ""),
        state.get("instructions", "")
    ))
    workflow.add_node("record_test", lambda state: visit_assistance.record_test_order(
        state,
        state.get("test_name", ""),
        state.get("test_type", ""),
        state.get("urgency", ""),
        state.get("test_instructions", "")
    ))
    workflow.add_node("end_visit", visit_assistance.end_visit)
    
    # Post-Visit
    workflow.add_node("create_post_visit_tasks", post_visit.create_post_visit_tasks)
    workflow.add_node("handle_prescription", lambda state: post_visit.handle_prescription_routing(state, state.get("pharmacy_choice", "hospital")))
    workflow.add_node("schedule_lab", lambda state: post_visit.schedule_lab_work(state, state.get("schedule_now", True)))
    workflow.add_node("schedule_follow_up", lambda state: post_visit.schedule_follow_up(state, state.get("preferred_date")))
    workflow.add_node("process_payment", lambda state: post_visit.process_payment(state, state.get("payment_method", "card")))
    workflow.add_node("generate_discharge", post_visit.generate_discharge_instructions)
    workflow.add_node("initiate_departure", post_visit.initiate_departure)
    workflow.add_node("complete_journey", post_visit.complete_journey)
    
    # Emergency
    workflow.add_node("detect_emergency", lambda state: emergency.detect_emergency(state, state.get("user_message", "")))
    workflow.add_node("handle_emergency", lambda state: emergency.handle_emergency(state, state.get("emergency_type", "general"), state.get("user_message", "")))
    workflow.add_node("resolve_emergency", emergency.resolve_emergency)
    workflow.add_node("provide_support", lambda state: emergency.provide_emotional_support(state, state.get("concern", "")))
    
    # ===== ROUTING LOGIC =====
    
    def route_by_stage(state: HospitalGuidanceState) -> str:
        """Route based on current journey stage"""
        
        # Check for emergency first
        if state.get("emergency_active"):
            return "handle_emergency"
        
        stage = state.get("journey_stage")
        
        if stage == JourneyStage.ARRIVAL:
            return "check_in"
        elif stage == JourneyStage.CHECK_IN:
            return "completing_check_in"
        elif stage == JourneyStage.PRE_VISIT or stage == JourneyStage.WAITING:
            return "waiting"
        elif stage == JourneyStage.IN_VISIT:
            return "in_visit"
        elif stage == JourneyStage.POST_VISIT:
            return "post_visit"
        elif stage == JourneyStage.DEPARTURE:
            return "departing"
        elif stage == JourneyStage.COMPLETED:
            return "end"
        
        return "arrival"
    
    def route_by_intent(state: HospitalGuidanceState) -> str:
        """Route based on user intent"""
        
        intent = state.get("user_intent", "")
        
        # Intent mapping
        intent_routes = {
            "navigate": "provide_navigation",
            "find_amenities": "find_amenities",
            "check_wait": "update_wait_time",
            "explain_term": "explain_term",
            "emergency": "handle_emergency",
            "support": "provide_support",
            "complete": "end"
        }
        
        return intent_routes.get(intent, "handle_arrival")
    
    # ===== EDGES =====
    
    # Entry point
    workflow.set_entry_point("handle_arrival")
    
    # Arrival flow
    workflow.add_edge("handle_arrival", "initiate_check_in")
    workflow.add_edge("initiate_check_in", "complete_check_in")
    workflow.add_edge("complete_check_in", "update_wait_time")
    
    # Waiting flow
    workflow.add_edge("update_wait_time", "suggest_activities")
    workflow.add_conditional_edges(
        "suggest_activities",
        lambda state: "visit" if state.get("queue_position") == 1 else "wait",
        {
            "visit": "start_visit",
            "wait": END
        }
    )
    
    # Visit flow
    workflow.add_edge("start_visit", "generate_questions")
    workflow.add_edge("generate_questions", END)
    workflow.add_edge("end_visit", "create_post_visit_tasks")
    
    # Post-visit flow
    workflow.add_edge("create_post_visit_tasks", "generate_discharge")
    workflow.add_edge("generate_discharge", "initiate_departure")
    workflow.add_conditional_edges(
        "initiate_departure",
        lambda state: "complete" if len(state.get("pending_tasks", [])) == 0 else "wait",
        {
            "complete": "complete_journey",
            "wait": END
        }
    )
    
    workflow.add_edge("complete_journey", END)
    
    # Emergency handling
    workflow.add_edge("handle_emergency", "resolve_emergency")
    workflow.add_edge("resolve_emergency", END)
    
    # Navigation
    workflow.add_edge("provide_navigation", END)
    workflow.add_edge("find_amenities", END)
    workflow.add_edge("update_location", END)
    
    # Support
    workflow.add_edge("provide_support", END)
    
    logger.info("Hospital guidance agent workflow compiled successfully")

    graph = workflow.compile()
    # mermaid = graph.draw_mermaid()
    # print(mermaid)
    return graph

# Create the agent
hospital_guidance_agent = create_hospital_guidance_agent()