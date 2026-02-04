from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta

from app.agents.hospital_guidance.state import HospitalGuidanceState, JourneyStage, PriorityLevel
from app.agents.hospital_guidance.tools.navigation_tool import navigation_tool
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

def create_post_visit_tasks(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Create list of post-visit tasks patient needs to complete"""
    
    tasks = []
    
    # Prescription pickup
    if state.get("prescriptions"):
        tasks.append({
            "task_id": "pickup_prescription",
            "type": "prescription",
            "priority": PriorityLevel.HIGH.value,
            "title": "Pick Up Prescription",
            "description": f"{len(state['prescriptions'])} medication(s) prescribed",
            "status": "pending",
            "options": [
                {
                    "name": "Hospital Pharmacy",
                    "location": "1st Floor",
                    "wait_time": "15 minutes"
                },
                {
                    "name": "External Pharmacy",
                    "location": "CVS on Main Street",
                    "wait_time": "2 hours"
                }
            ]
        })
    
    # Lab work
    if state.get("tests_ordered"):
        incomplete_tests = [
            test for test in state["tests_ordered"]
            if not test.get("completed", False)
        ]
        
        if incomplete_tests:
            tasks.append({
                "task_id": "complete_lab_work",
                "type": "lab",
                "priority": PriorityLevel.HIGH.value if any(t.get("urgency") == "urgent" for t in incomplete_tests) else PriorityLevel.MEDIUM.value,
                "title": "Complete Lab Work",
                "description": f"{len(incomplete_tests)} test(s) ordered",
                "status": "pending",
                "tests": incomplete_tests,
                "location": "Hospital Lab - 2nd Floor"
            })
    
    # Follow-up appointment
    if state.get("follow_up_needed"):
        tasks.append({
            "task_id": "schedule_follow_up",
            "type": "appointment",
            "priority": PriorityLevel.MEDIUM.value,
            "title": "Schedule Follow-up Appointment",
            "description": f"Follow-up with Dr. {state['doctor_name']}",
            "status": "pending",
            "recommended_timeframe": state.get("follow_up_date", "2 weeks")
        })
    
    # Billing/payment
    if not state.get("copay_paid"):
        tasks.append({
            "task_id": "complete_payment",
            "type": "billing",
            "priority": PriorityLevel.LOW.value,
            "title": "Complete Payment",
            "description": "Copay and billing",
            "status": "pending",
            "amount": "$45.00"
        })
    
    logger.info(f"Created {len(tasks)} post-visit tasks for patient {state['patient_id']}")
    
    return {
        **state,
        "pending_tasks": tasks,
        "last_updated": datetime.now()
    }


def handle_prescription_routing(
    state: HospitalGuidanceState,
    pharmacy_choice: str
) -> Dict[str, Any]:
    """Route prescription to chosen pharmacy"""
    
    logger.info(f"Routing prescription to: {pharmacy_choice}")
    
    if pharmacy_choice == "hospital":
        # Navigate to hospital pharmacy
        pharmacy = navigation_tool.find_location("pharmacy")
        
        route = None
        if pharmacy and state.get("current_location"):
            route = navigation_tool.calculate_route(
                state["current_location"],
                pharmacy
            )
        
        notification = {
            "type": "info",
            "title": "Prescription Sent to Hospital Pharmacy",
            "message": f"Your prescription will be ready in 15 minutes. I'll guide you to the pharmacy.",
            "route": route,
            "timestamp": datetime.now()
        }
        
        # Update task status
        tasks = state.get("pending_tasks", [])
        for task in tasks:
            if task.get("task_id") == "pickup_prescription":
                task["status"] = "in_progress"
                task["location"] = pharmacy
        
        return {
            **state,
            "destination": pharmacy,
            "navigation_route": route["steps"] if route else None,
            "navigation_active": True,
            "pending_tasks": tasks,
            "notifications": state.get("notifications", []) + [notification],
            "last_updated": datetime.now()
        }
    
    else:  # External pharmacy
        notification = {
            "type": "success",
            "title": "Prescription Sent",
            "message": f"Your prescription has been sent to {pharmacy_choice}. It will be ready in about 2 hours.",
            "timestamp": datetime.now()
        }
        
        # Mark task as completed
        tasks = state.get("pending_tasks", [])
        completed = state.get("completed_tasks", [])
        
        for task in tasks:
            if task.get("task_id") == "pickup_prescription":
                task["status"] = "completed"
                completed.append("pickup_prescription")
        
        return {
            **state,
            "pending_tasks": [t for t in tasks if t.get("status") != "completed"],
            "completed_tasks": completed,
            "notifications": state.get("notifications", []) + [notification],
            "last_updated": datetime.now()
        }


def schedule_lab_work(state: HospitalGuidanceState, schedule_now: bool) -> Dict[str, Any]:
    """Schedule or complete lab work"""
    
    if schedule_now:
        # Navigate to lab
        lab = navigation_tool.find_location("lab")
        
        route = None
        if lab and state.get("current_location"):
            route = navigation_tool.calculate_route(
                state["current_location"],
                lab
            )
        
        notification = {
            "type": "info",
            "title": "Proceeding to Lab",
            "message": "Current wait time at the lab is approximately 10 minutes. I'll guide you there.",
            "route": route,
            "timestamp": datetime.now()
        }
        
        # Update task
        tasks = state.get("pending_tasks", [])
        for task in tasks:
            if task.get("task_id") == "complete_lab_work":
                task["status"] = "in_progress"
        
        return {
            **state,
            "destination": lab,
            "navigation_route": route["steps"] if route else None,
            "navigation_active": True,
            "pending_tasks": tasks,
            "notifications": state.get("notifications", []) + [notification],
            "last_updated": datetime.now()
        }
    
    else:
        # Schedule for later
        notification = {
            "type": "info",
            "title": "Lab Work Scheduled",
            "message": "You can complete lab work at your convenience. I'll send you a reminder.",
            "timestamp": datetime.now()
        }
        
        return {
            **state,
            "notifications": state.get("notifications", []) + [notification],
            "last_updated": datetime.now()
        }


def schedule_follow_up(
    state: HospitalGuidanceState,
    preferred_date: datetime
) -> Dict[str, Any]:
    """Schedule follow-up appointment"""
    
    logger.info(f"Scheduling follow-up for {preferred_date}")
    
    # In production, this would integrate with hospital scheduling system
    # For now, simulate successful scheduling
    
    notification = {
        "type": "success",
        "title": "Follow-up Scheduled",
        "message": f"Your follow-up appointment with Dr. {state['doctor_name']} is scheduled for {preferred_date.strftime('%B %d, %Y at %I:%M %p')}. You'll receive a reminder 24 hours before.",
        "timestamp": datetime.now()
    }
    
    # Update task
    tasks = state.get("pending_tasks", [])
    completed = state.get("completed_tasks", [])
    
    for task in tasks:
        if task.get("task_id") == "schedule_follow_up":
            task["status"] = "completed"
            completed.append("schedule_follow_up")
    
    return {
        **state,
        "follow_up_date": preferred_date,
        "pending_tasks": [t for t in tasks if t.get("status") != "completed"],
        "completed_tasks": completed,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def process_payment(state: HospitalGuidanceState, payment_method: str) -> Dict[str, Any]:
    """Process payment/copay"""
    
    logger.info(f"Processing payment via {payment_method}")
    
    # Simulate payment processing
    notification = {
        "type": "success",
        "title": "Payment Processed",
        "message": f"Your copay of $45.00 has been processed via {payment_method}. Receipt sent to your email.",
        "timestamp": datetime.now()
    }
    
    # Update task
    tasks = state.get("pending_tasks", [])
    completed = state.get("completed_tasks", [])
    
    for task in tasks:
        if task.get("task_id") == "complete_payment":
            task["status"] = "completed"
            completed.append("complete_payment")
    
    return {
        **state,
        "copay_paid": True,
        "pending_tasks": [t for t in tasks if t.get("status") != "completed"],
        "completed_tasks": completed,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def generate_discharge_instructions(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Generate comprehensive discharge instructions"""
    
    logger.info("Generating discharge instructions")
    
    llm = get_llm()
    instructions_prompt = f"""
    Generate comprehensive discharge instructions for a patient.
    
    Visit information:
    - Doctor: {state['doctor_name']}
    - Diagnosis: {state.get('diagnosis', 'Not specified')}
    - Prescriptions: {len(state.get('prescriptions', []))} medications
    - Tests ordered: {len(state.get('tests_ordered', []))} tests
    - Follow-up: {state.get('follow_up_needed', False)}
    
    Visit summary: {state.get('visit_summary', '')}
    
    Create clear discharge instructions with sections:
    1. What to Do at Home
    2. Medications (how and when to take)
    3. Warning Signs (when to seek help)
    4. Follow-up Care
    5. Lifestyle Recommendations
    
    Make it actionable, clear, and reassuring. Use bullet points.
    """
    
    try:
        instructions_response = llm.invoke(instructions_prompt)
        instructions = instructions_response.content
    except Exception as e:
        logger.error(f"Error generating instructions: {e}")
        instructions = f"""
        Discharge Instructions:
        
        1. Take medications as prescribed
        2. Monitor your symptoms
        3. Contact your doctor if symptoms worsen
        4. Attend your follow-up appointment
        """
    
    return {
        **state,
        "notifications": state.get("notifications", []) + [{
            "type": "discharge_instructions",
            "title": "Discharge Instructions",
            "message": instructions,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def initiate_departure(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Prepare for patient departure"""
    
    # Check for incomplete tasks
    pending_tasks = [
        task for task in state.get("pending_tasks", [])
        if task.get("status") != "completed"
    ]
    
    if pending_tasks:
        # Remind about pending tasks
        task_list = "\n".join([f"• {task['title']}" for task in pending_tasks])
        
        notification = {
            "type": "warning",
            "title": "Pending Tasks",
            "message": f"You have {len(pending_tasks)} task(s) to complete before leaving:\n{task_list}\n\nWould you like to complete them now?",
            "pending_tasks": pending_tasks,
            "timestamp": datetime.now()
        }
    else:
        # All tasks complete - provide exit navigation
        exit_location = navigation_tool.find_location("exit")
        route = None
        
        if exit_location and state.get("current_location"):
            route = navigation_tool.calculate_route(
                state["current_location"],
                exit_location
            )
        
        notification = {
            "type": "success",
            "title": "Ready to Leave",
            "message": "All tasks complete! Thank you for visiting. I'll guide you to the exit.",
            "route": route,
            "timestamp": datetime.now()
        }
    
    return {
        **state,
        "journey_stage": JourneyStage.DEPARTURE,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": datetime.now()
    }


def complete_journey(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Mark hospital journey as complete"""
    
    logger.info(f"Journey completed for patient {state['patient_id']}")
    
    # Generate final summary
    llm = get_llm()
    summary_prompt = f"""
    Generate a warm, encouraging final message for a patient completing their hospital visit.
    
    Visit details:
    - Doctor: {state['doctor_name']}
    - Completed tasks: {len(state.get('completed_tasks', []))}
    - Prescriptions: {len(state.get('prescriptions', []))}
    - Follow-up scheduled: {state.get('follow_up_needed', False)}
    
    Include:
    - Thank them for choosing this hospital
    - Remind them about follow-up care
    - Offer continued support via the app
    - Wish them well
    
    Keep it warm and brief (3-4 sentences).
    """
    
    try:
        farewell_response = llm.invoke(summary_prompt)
        farewell = farewell_response.content
    except Exception as e:
        logger.error(f"Error generating farewell: {e}")
        farewell = "Thank you for visiting us today. Take care and feel better soon!"
    
    # Request feedback
    feedback_request = {
        "type": "feedback_request",
        "title": "How Was Your Experience?",
        "message": "We'd love to hear about your visit today. Your feedback helps us improve.",
        "timestamp": datetime.now()
    }
    
    return {
        **state,
        "journey_stage": JourneyStage.COMPLETED,
        "notifications": state.get("notifications", []) + [
            {
                "type": "success",
                "title": "Journey Complete",
                "message": farewell,
                "timestamp": datetime.now()
            },
            feedback_request
        ],
        "last_updated": datetime.now()
    }