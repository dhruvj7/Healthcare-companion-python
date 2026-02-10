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


def provide_navigation(state: HospitalGuidanceState) -> Dict[str, Any]:
    """Provide navigation to a destination"""
    
    # Extract destination query from state (multiple sources)
    destination_query = (
        state.get("navigation_query") or  # Set by orchestrator
        state.get("location_query") or    # Alternative key
        state.get("user_message", "")     # Fallback to full message
    )
    
    # Clean up the query - extract just the location name
    destination_query = extract_destination_with_llm(destination_query)
    
    logger.info(f"Navigation requested to: '{destination_query}'")
    
    if not destination_query:
        return {
            **state,
            "agent_message": "Where would you like to go? I can help you navigate to any location in the hospital.",
            "suggested_locations": [
                "Cafeteria", "Pharmacy", "Laboratory", "Emergency Room", 
                "Registration", "Waiting Room", "Restrooms"
            ],
            "last_updated": datetime.now()
        }
    
    # Find destination
    destination = navigation_tool.find_location(destination_query)
    
    if not destination:
        common_locations = [
            "Main Entrance", "Registration", "Emergency Room",
            "Cafeteria", "Pharmacy", "Waiting Room", "Laboratory"
        ]
        
        return {
            **state,
            "agent_message": f"I couldn't find '{destination_query}'. Here are some common locations I can help you navigate to:\n\n" + 
                           "\n".join([f"• {loc}" for loc in common_locations]),
            "suggested_locations": common_locations,
            "last_updated": datetime.now()
        }
    
    # Get current location
    current_location = state.get("current_location")
    
    if not current_location:
        # No current location - provide destination info only
        return {
            **state,
            "destination": destination,
            "agent_message": f"**{destination['name']}** is located in:\n\n" +
                           f"🏢 {destination['building_name']}\n" +
                           f"📍 Floor {destination['floor']}\n\n" +
                           "To get detailed turn-by-turn directions, please share your current location.",
            "last_updated": datetime.now()
        }
    
    # Calculate route
    route = navigation_tool.calculate_route(current_location, destination)
    
    # ✅ Generate conversational directions using LLM
    llm = get_llm()
    
    # Prepare route info for LLM
    steps_list = [step['instruction'] for step in route['steps']]
    est_minutes = route['estimated_time'] // 60
    est_seconds = route['estimated_time'] % 60
    
    directions_prompt = f"""
You are a friendly hospital navigation assistant. Convert these navigation steps into warm, conversational directions.

**Destination:** {destination['name']}
**From:** {current_location.get('name', 'your current location')}

**Steps:**
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(steps_list)])}

**Distance:** {int(route['distance'])} feet
**Estimated time:** {f"{est_minutes} minute{'s' if est_minutes != 1 else ''}" if est_minutes > 0 else f"{est_seconds} seconds"}
**Wheelchair accessible:** {"Yes" if route.get('accessible') else "No"}

**Instructions:**
1. Make it sound natural and friendly, like a helpful guide
2. Keep it concise but clear (4-6 sentences max)
3. Include the key turns and landmarks
4. Mention the estimated time naturally
5. End with an encouraging note

Format as plain text with natural paragraphs (no markdown headers, no bullet points).
"""
    
    try:
        directions_response = llm.invoke(directions_prompt)
        conversational_directions = directions_response.content.strip()
    except Exception as e:
        logger.error(f"Error generating conversational directions: {e}")
        # Fallback to simple format
        conversational_directions = (
            f"To get to {destination['name']}, {steps_list[0].lower()}. "
            f"It will take about {est_minutes if est_minutes > 0 else 1} minute{'s' if est_minutes != 1 else ''}. "
            f"You'll arrive at {destination['name']} shortly."
        )
    
    return {
        **state,
        "destination": destination,
        "current_route": route,
        "navigation_active": True,
        "agent_message": conversational_directions,  # ✅ LLM-generated conversational text
        "last_updated": datetime.now()
    }


def extract_destination_with_llm(message: str, llm) -> str:
    """Use LLM to reliably extract destination"""
    
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    prompt = ChatPromptTemplate.from_template("""
Extract ONLY the destination location from this query. Return just the location name.

Examples:
- "Where is cafeteria?" → cafeteria
- "How do I get to the emergency room?" → emergency room
- "Take me to pharmacy" → pharmacy
- "Find the nearest restroom" → restroom
- "Room 302 please" → room 302

Query: {message}

Location (one or two words only):""")
    
    try:
        destination = (
            prompt 
            | llm 
            | StrOutputParser()
        ).invoke({"message": message}).strip().lower()
        
        return destination
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}, using fallback")
        return message.strip()

