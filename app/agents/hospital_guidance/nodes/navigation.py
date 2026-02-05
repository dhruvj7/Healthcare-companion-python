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
        return {
            **state,
            "nearby_amenities": [],
            "amenities_last_updated": None
        }
    
    # Get amenities from navigation tool
    amenities = navigation_tool.get_nearby_amenities(state["current_location"])
    
    # Enrich amenities with additional info
    enriched_amenities = []
    current_time = datetime.now()
    
    for amenity in amenities:
        enriched = {
            **amenity,
            "id": f"amenity_{amenity['type']}_{amenity['name'].lower().replace(' ', '_')}",
            "available": True,  # Default
            "currently_open": True  # Default
        }
        
        # Add hours and check if open (if applicable)
        if amenity["type"] in ["food", "pharmacy", "shop"]:
            hours = _get_amenity_hours(amenity["name"])
            enriched["hours"] = hours
            enriched["currently_open"] = _is_currently_open(hours, current_time)
        
        # Add accessibility info
        enriched["wheelchair_accessible"] = amenity.get("accessible", True)
        
        # Add directions
        enriched["direction"] = _get_direction(
            state["current_location"]["coordinates"],
            amenity.get("coordinates", {})
        )
        
        enriched_amenities.append(enriched)
    
    # Create a summary notification (optional)
    notification = {
        "type": "info",
        "title": "Nearby Amenities Updated",
        "message": f"Found {len(enriched_amenities)} nearby amenities",
        "timestamp": current_time,
        "action": "view_amenities" 
    }
    
    return {
        **state,
        "nearby_amenities": enriched_amenities,  # ← Separate key
        "amenities_last_updated": current_time,
        "notifications": state.get("notifications", []) + [notification],
        "last_updated": current_time
    }


def _get_amenity_hours(amenity_name: str) -> str:
    """Get operating hours for amenity"""
    hours_map = {
        "cafeteria": "6:00 AM - 8:00 PM",
        "pharmacy": "8:00 AM - 6:00 PM",
        "gift shop": "9:00 AM - 5:00 PM",
        "lab": "7:00 AM - 5:00 PM"
    }
    
    for key, hours in hours_map.items():
        if key in amenity_name.lower():
            return hours
    
    return "24/7"  # Default for restrooms, etc.


def _is_currently_open(hours: str, current_time: datetime) -> bool:
    """Check if amenity is currently open"""
    if hours == "24/7":
        return True
    
    # Parse hours (simplified - production would be more robust)
    try:
        # "8:00 AM - 6:00 PM" → parse and compare
        # Simplified logic
        current_hour = current_time.hour
        
        if "AM" in hours and "PM" in hours:
            # Extract opening and closing hours
            parts = hours.split(" - ")
            open_time = int(parts[0].split(":")[0])
            close_time = int(parts[1].split(":")[0])
            
            if "PM" in parts[1] and close_time != 12:
                close_time += 12
            
            return open_time <= current_hour < close_time
        
        return True  # Default to open if can't parse
    except:
        return True


def _get_direction(from_coords: Dict, to_coords: Dict) -> str:
    """Get cardinal direction (N, S, E, W, etc.)"""
    if not from_coords or not to_coords:
        return "nearby"
    
    dx = to_coords.get("x", 0) - from_coords.get("x", 0)
    dy = to_coords.get("y", 0) - from_coords.get("y", 0)
    
    if abs(dx) > abs(dy):
        return "east" if dx > 0 else "west"
    else:
        return "north" if dy > 0 else "south"


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
    
    # Update location
    updated_state = {
        **state,
        "current_location": new_location,
        "navigation_active": not destination_reached,
        "notifications": state.get("notifications", []) + ([notification] if notification else []),
        "last_updated": datetime.now()
    }
    
    # AUTO-UPDATE AMENITIES when location changes
    updated_state = find_nearby_amenities(updated_state)
    
    return updated_state