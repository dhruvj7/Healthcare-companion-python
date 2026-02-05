from typing import Dict, Optional, List
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)

class QueueManagementTool:
    """Manage patient queue and wait times"""
    
    def __init__(self):
        # In production, this would connect to hospital's queue system
        self.queues = {}  # doctor_id -> queue
    
    def add_to_queue(
        self, 
        patient_id: str, 
        doctor_id: str, 
        appointment_time: datetime
    ) -> Dict:
        """Add patient to doctor's queue"""
        
        if doctor_id not in self.queues:
            self.queues[doctor_id] = []
        
        queue_entry = {
            "patient_id": patient_id,
            "appointment_time": appointment_time,
            "check_in_time": datetime.now(),
            "status": "waiting"
        }
        
        self.queues[doctor_id].append(queue_entry)
        
        position = len(self.queues[doctor_id])
        
        logger.info(f"Patient {patient_id} added to queue for {doctor_id}, position {position}")
        
        return {
            "queue_position": position,
            "estimated_wait": self._estimate_wait_time(doctor_id, position),
            "patients_ahead": position - 1
        }
    
    def get_queue_status(self, patient_id: str, doctor_id: str) -> Optional[Dict]:
        """Get current queue status for a patient"""
        
        if doctor_id not in self.queues:
            return None
        
        for idx, entry in enumerate(self.queues[doctor_id], 1):
            if entry["patient_id"] == patient_id:
                return {
                    "queue_position": idx,
                    "estimated_wait": self._estimate_wait_time(doctor_id, idx),
                    "patients_ahead": idx - 1,
                    "status": entry["status"],
                    "check_in_time": entry["check_in_time"],
                    "last_updated": datetime.now()
                }
        
        return None
    
    def _estimate_wait_time(self, doctor_id: str, position: int) -> int:
        """Estimate wait time in minutes"""
        # Simulate variable wait times
        # In production, this would use historical data and ML
        
        base_time_per_patient = random.randint(15, 25)  # 15-25 min per patient
        current_delay = random.randint(0, 15)  # Random delays
        
        estimated_minutes = (position - 1) * base_time_per_patient + current_delay
        
        return max(0, estimated_minutes)
    
    def update_queue(self, doctor_id: str) -> None:
        """Update queue (called when patient is seen)"""
        
        if doctor_id in self.queues and self.queues[doctor_id]:
            # Mark first patient as being seen
            self.queues[doctor_id][0]["status"] = "in_visit"
            
            # After visit completes, remove them
            # (In real system, this would be triggered by doctor's actions)
    
    def remove_from_queue(self, patient_id: str, doctor_id: str) -> bool:
        """Remove patient from queue"""
        
        if doctor_id not in self.queues:
            return False
        
        original_length = len(self.queues[doctor_id])
        self.queues[doctor_id] = [
            entry for entry in self.queues[doctor_id]
            if entry["patient_id"] != patient_id
        ]
        
        return len(self.queues[doctor_id]) < original_length
    
    def is_ready_for_patient(self, patient_id: str, doctor_id: str) -> bool:
        """Check if patient is next in queue"""
        
        if doctor_id not in self.queues or not self.queues[doctor_id]:
            return False
        
        return self.queues[doctor_id][0]["patient_id"] == patient_id

# Singleton instance
queue_tool = QueueManagementTool()