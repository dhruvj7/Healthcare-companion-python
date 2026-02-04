from typing import Dict, Any
import logging
from datetime import datetime

from app.agents.hospital_guidance.state import HospitalGuidanceState
from app.agents.hospital_guidance.tools.navigation_tool import navigation_tool
from app.services.llm_service import get_llm

logger = logging.getLogger(__name__)

def provide_navigation(state: HospitalGuidanceState, destination_query: str) -> Dict[str, Any]:
    """Provide navigation to a destination"""
    
    logger.info(f"Navigation requested to: {destination_query}")
    
    # Find destination
    destination = navigation_tool.find_location(destination_query)
    
    if not destination:
        return {
            **state,
            "notifications": state.get("notifications", []) + [{
                "type": "error",
                "message": f"Could not find location: {destination_query}",
                "timestamp": datetime.now()
            }]
        }
    
    # Calculate route
    if not state.get("current_location"):
        return {
            **state,
            "notifications": state.get("notifications", []) + [{
                "type": "error",
                "message": "Current location unknown. Please enable location services.",
                "timestamp": datetime.now()
            }]
        }
    
    route = navigation_tool.calculate_route(
        state["current_location"],
        destination
    )
    
    # Generate conversational directions
    llm = get_llm()
    directions_prompt = f"""
    Convert these navigation steps into friendly, conversational directions.
    
    Steps:
    {[step['instruction'] for step in route['steps']]}
    
    Estimated time: {route['estimated_time']} seconds
    
    Make it sound natural and helpful, like a friend giving directions.
    Keep it concise (3-4 sentences max).
    """
    
    try:
        directions_response = llm.invoke(directions_prompt)
        conversational_directions = directions_response.content
    except Exception as e:
        logger.error(f"Error generating directions: {e}")
        conversational_directions = f"Navigate to {destination['name']}. It will take about {route['estimated_time'] // 60} minutes."
    
    return {
        **state,
        "destination": destination,
        "navigation_route": route["steps"],
        "navigation_active": True,
        "notifications": state.get("notifications", []) + [{
            "type": "navigation",
            "title": f"Directions to {destination['name']}",
            "message": conversational_directions,
            "route": route,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def find_nearby_amenities(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Find nearby restrooms, cafeteria, etc."""
    
    if not state.get("current_location"):
        return state
    
    amenities = navigation_tool.get_nearby_amenities(state["current_location"])
    
    # Format amenities message
    amenities_list = []
    for amenity in amenities:
        walk_time = amenity["walking_time"]
        amenities_list.append(
            f"• {amenity['name']} - {walk_time} second walk"
        )
    
    message = "Nearby amenities:\n" + "\n".join(amenities_list)
    
    return {
        **state,
        "notifications": state.get("notifications", []) + [{
            "type": "info",
            "title": "Nearby Amenities",
            "message": message,
            "amenities": amenities,
            "timestamp": datetime.now()
        }],
        "last_updated": datetime.now()
    }


def update_location(state: HospitalGuidanceState, new_location: Dict[str, Any]) -> Dict[str, Any]:
    """Update patient's current location"""
    
    logger.info(f"Location updated to: {new_location.get('name', 'Unknown')}")
    
    # Check if reached destination
    destination_reached = False
    if state.get("destination"):
        if (new_location.get("room") == state["destination"].get("room") and
            new_location.get("floor") == state["destination"].get("floor")):
            destination_reached = True
    
    notification = None
    if destination_reached:
        notification = {
            "type": "success",
            "title": "Destination Reached",
            "message": f"You've arrived at {state['destination']['name']}",
            "timestamp": datetime.now()
        }
    
    return {
        **state,
        "current_location": new_location,
        "navigation_active": not destination_reached,
        "notifications": state.get("notifications", []) + ([notification] if notification else []),
        "last_updated": datetime.now()
    }