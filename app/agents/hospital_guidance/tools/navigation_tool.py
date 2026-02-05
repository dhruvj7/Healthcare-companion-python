from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class NavigationTool:
    """Indoor navigation and wayfinding"""
    
    def __init__(self, hospital_layout_file: str = "app/data/hospital_layout.json"):
        self.hospital_layout = self._load_layout(hospital_layout_file)
        self.waypoint_graph = self._build_graph()
    
    def _load_layout(self, file_path: str) -> Dict:
        """Load hospital floor plan data"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load hospital layout: {e}")
            return self._get_default_layout()
    
    def _get_default_layout(self) -> Dict:
        """Default hospital layout for demo purposes"""
        return {
            "buildings": {
                "A": {
                    "name": "Main Building",
                    "floors": {
                        "1": {
                            "locations": {
                                "main_entrance": {"x": 0, "y": 0, "name": "Main Entrance"},
                                "registration": {"x": 20, "y": 0, "name": "Registration Desk"},
                                "elevator_a": {"x": 50, "y": 0, "name": "Elevator A"},
                                "cafeteria": {"x": 80, "y": 0, "name": "Cafeteria"},
                                "pharmacy": {"x": 100, "y": 0, "name": "Pharmacy"}
                            }
                        },
                        "2": {
                            "locations": {
                                "waiting_room_2a": {"x": 10, "y": 20, "name": "Waiting Room 2A"},
                                "exam_room_201": {"x": 30, "y": 20, "name": "Exam Room 201"},
                                "exam_room_205": {"x": 50, "y": 20, "name": "Exam Room 205"},
                                "lab": {"x": 80, "y": 20, "name": "Laboratory"}
                            }
                        },
                        "3": {
                            "locations": {
                                "cardiology": {"x": 20, "y": 30, "name": "Cardiology Department"},
                                "dr_smith_office": {"x": 40, "y": 30, "name": "Dr. Smith's Office - Room 305"}
                            }
                        }
                    }
                },
                "B": {
                    "name": "Medical Tower",
                    "floors": {
                        "1": {
                            "locations": {
                                "imaging": {"x": 0, "y": 50, "name": "Imaging Center"}
                            }
                        }
                    }
                }
            }
        }
    
    def _build_graph(self) -> Dict:
        """Build navigation graph (simplified)"""
        # In production, this would use A* pathfinding
        return {}
    
    def find_location(self, query: str, building: str = None, floor: str = None) -> Optional[Dict]:
        """Find a location by name or query"""
        query_lower = query.lower()
        
        for building_id, building_data in self.hospital_layout["buildings"].items():
            if building and building != building_id:
                continue
                
            for floor_id, floor_data in building_data["floors"].items():
                if floor and floor != floor_id:
                    continue
                    
                for loc_id, loc_data in floor_data["locations"].items():
                    if query_lower in loc_data["name"].lower() or query_lower in loc_id:
                        return {
                            "building": building_id,
                            "building_name": building_data["name"],
                            "floor": floor_id,
                            "room": loc_id,
                            "name": loc_data["name"],
                            "coordinates": {"x": loc_data["x"], "y": loc_data["y"]}
                        }
        
        return None
    
    def calculate_route(
        self, 
        from_location: Dict[str, Any], 
        to_location: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate route between two locations"""
        
        # Same building and floor - simple route
        if (from_location["building"] == to_location["building"] and 
            from_location["floor"] == to_location["floor"]):
            
            distance = self._calculate_distance(
                from_location["coordinates"],
                to_location["coordinates"]
            )
            
            return {
                "distance": distance,
                "estimated_time": int(distance / 3),  # Assume 3 feet per second walking
                "steps": [
                    {
                        "instruction": f"Walk straight {int(distance)} feet",
                        "distance": distance,
                        "type": "walk"
                    },
                    {
                        "instruction": f"You'll arrive at {to_location['name']}",
                        "type": "arrival"
                    }
                ],
                "accessible": True
            }
        
        # Different floors - need elevator
        elif from_location["building"] == to_location["building"]:
            return {
                "distance": 150,
                "estimated_time": 4 * 60,  # 4 minutes
                "steps": [
                    {
                        "instruction": "Walk to Elevator A",
                        "distance": 50,
                        "type": "walk"
                    },
                    {
                        "instruction": f"Take elevator to Floor {to_location['floor']}",
                        "type": "elevator"
                    },
                    {
                        "instruction": f"Turn right and walk 50 feet",
                        "distance": 50,
                        "type": "walk"
                    },
                    {
                        "instruction": f"You'll arrive at {to_location['name']}",
                        "type": "arrival"
                    }
                ],
                "accessible": True
            }
        
        # Different buildings
        else:
            return {
                "distance": 300,
                "estimated_time": 8 * 60,  # 8 minutes
                "steps": [
                    {
                        "instruction": f"Exit {from_location['building_name']}",
                        "distance": 100,
                        "type": "walk"
                    },
                    {
                        "instruction": f"Walk to {to_location['building_name']} entrance",
                        "distance": 150,
                        "type": "outdoor_walk"
                    },
                    {
                        "instruction": f"Enter building and navigate to {to_location['name']}",
                        "distance": 50,
                        "type": "walk"
                    }
                ],
                "accessible": True
            }
    
    def _calculate_distance(self, coord1: Dict, coord2: Dict) -> float:
        """Calculate Euclidean distance between two points"""
        import math
        return math.sqrt((coord2["x"] - coord1["x"])**2 + (coord2["y"] - coord1["y"])**2)
    
    def get_nearby_amenities(self, location: Dict[str, Any]) -> List[Dict]:
        """Find nearby restrooms, cafeteria, etc."""
        amenities = []
        
        # Get all locations on same floor
        building = self.hospital_layout["buildings"].get(location["building"], {})
        floor_data = building.get("floors", {}).get(location["floor"], {})
        
        for loc_id, loc_data in floor_data.get("locations", {}).items():
            if loc_id != location.get("room"):
                distance = self._calculate_distance(
                    location["coordinates"],
                    {"x": loc_data["x"], "y": loc_data["y"]}
                )
                
                amenities.append({
                    "name": loc_data["name"],
                    "type": self._categorize_location(loc_data["name"]),
                    "distance": distance,
                    "walking_time": int(distance / 3)
                })
        
        # Sort by distance
        amenities.sort(key=lambda x: x["distance"])
        return amenities[:5]  # Top 5 nearest
    
    def _categorize_location(self, name: str) -> str:
        """Categorize location type"""
        name_lower = name.lower()
        if "cafeteria" in name_lower or "cafe" in name_lower:
            return "food"
        elif "restroom" in name_lower or "bathroom" in name_lower:
            return "restroom"
        elif "pharmacy" in name_lower:
            return "pharmacy"
        elif "lab" in name_lower:
            return "lab"
        else:
            return "other"

# Singleton instance
navigation_tool = NavigationTool()