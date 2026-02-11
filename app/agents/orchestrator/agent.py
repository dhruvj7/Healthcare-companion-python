import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from app.agents.hospital_guidance.state import JourneyStage
from app.services.intent_classifier import classify_intent, IntentType
from app.services.intent_classifier import (
    classify_intents,
    IntentType,
    MultiIntentClassificationResult,
)

from app.agents.symptom_analysis.agent import symptom_agent
from app.agents.hospital_guidance.agent import hospital_guidance_agent
from app.agents.doctor_finder.agent import doctor_agent
from app.services.llm_service import get_llm
from app.services.insurance_verifier import verify_insurance

logger = logging.getLogger(__name__)


class HealthcareOrchestrator:

    def __init__(self):
        self.llm = get_llm()
        self.conversation_sessions: Dict[str, List[Dict[str, Any]]] = {}
        self.journey_sessions: Dict[str, Dict[str, Any]] = {}

    # =====================================================
    # 🔥 MAIN ENTRY (MULTI-INTENT ENABLED)
    # =====================================================

    async def process_request(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:12]}"

        conversation_history = self.conversation_sessions.get(session_id, [])

        conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        classification: MultiIntentClassificationResult = classify_intents(
            user_input=user_input,
            conversation_history=conversation_history
        )

        logger.info(f"Detected intents: {[i.value for i in classification.intents]}")

        results: List[Dict[str, Any]] = []

        # 🚨 Emergency override
        if IntentType.EMERGENCY in classification.intents:
            result = self._handle_emergency(
                user_input,
                classification.extracted_entities
            )
            result["intent"] = IntentType.EMERGENCY.value
            results.append(result)
        else:
            for intent in classification.execution_order:
                result = await self._execute_intent(
                    intent=intent,
                    user_input=user_input,
                    entities=classification.extracted_entities,
                    session_id=session_id
                )
                result["intent"] = intent.value
                results.append(result)

        final_result = self._merge_results(results)

        conversation_history.append({
            "role": "assistant",
            "content": final_result.get("message", ""),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        self.conversation_sessions[session_id] = conversation_history[-20:]

        return {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_input": user_input,
            "intents": [i.value for i in classification.intents],
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "result": final_result
        }

    # =====================================================
    # 🔥 INTENT EXECUTOR
    # =====================================================

    async def _execute_intent(
        self,
        intent: IntentType,
        user_input: str,
        entities: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:

        if intent == IntentType.SYMPTOM_ANALYSIS:
            return await self._handle_symptom_analysis(
                user_input, entities, session_id
            )

        elif intent == IntentType.INSURANCE_VERIFICATION:
            return self._handle_insurance_verification(
                user_input, entities, session_id
            )

        elif intent == IntentType.APPOINTMENT_BOOKING:
            return self._handle_appointment_booking(
                user_input, entities, session_id
            )

        elif intent == IntentType.HOSPITAL_NAVIGATION:
            return self._handle_hospital_navigation(
                user_input, entities, session_id
            )

        elif intent == IntentType.GENERAL_HEALTH_QUESTION:
            return self._handle_general_question(
                user_input, entities
            )
        
        elif intent == IntentType.HOSPITAL_NAVIGATION:
                return await self._handle_hospital_navigation(
                user_input, 
                extracted_entities, 
                session_id,
                additional_context
            )

        else:
            return self._handle_unknown_intent(user_input)

    # =====================================================
    # 🔥 MERGE MULTIPLE RESULTS
    # =====================================================

    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:

        if len(results) == 1:
            return results[0]

        combined_message = "\n\n".join(
            r.get("message", "") for r in results if r.get("message")
        )

        # Priority resolution
        priority_order = [
            "emergency",
            "error",
            "verification_failed",
            "needs_more_info"
        ]

        overall_status = "multi_intent_success"

        for status in priority_order:
            if any(r.get("status") == status for r in results):
                overall_status = status
                break

        return {
            "status": overall_status,
            "message": combined_message,
            "sub_results": results
            }
    
    def _handle_emergency(self, user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency situations"""
        logger.critical(f"EMERGENCY detected: {user_input}")

        return {
            "status": "emergency",
            "message": "🚨 EMERGENCY DETECTED - Please call emergency services immediately!",
            "emergency_instructions": [
                "📞 Call 911 (US) or 108 (India) or your local emergency number IMMEDIATELY",
                "🏥 Do not drive yourself - call an ambulance",
                "👨‍👩‍👧 Inform a family member or friend",
                "📍 Share your location with emergency services",
                "⏱️ Note the time symptoms started"
            ],
            "symptoms": entities.get("symptoms", [user_input]),
            "severity": "CRITICAL",
            "requires_immediate_action": True,
            "disclaimer": "⚠️ This is a medical emergency. Call emergency services immediately. Do not wait."
        }

    async def _handle_symptom_analysis(self, user_input: str, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle symptom analysis using the symptom analysis agent"""
        logger.info("Handling symptom analysis request")

        # Extract or prompt for required information
        symptoms = entities.get("symptoms", [user_input])
        duration = entities.get("duration", "not specified")
        age = entities.get("age")
        severity = entities.get("severity_1_10")
        existing_conditions = entities.get("existing_conditions", [])
        medications = entities.get("medications", [])
        allergies = entities.get("allergies", [])

        # Check if we have minimum required information
        if not symptoms or (isinstance(symptoms, list) and len(symptoms) == 0):
            return {
                "status": "needs_more_info",
                "message": "I'd be happy to help analyze your symptoms. Could you please describe what symptoms you're experiencing?",
                "required_fields": ["symptoms"]
            }

        # Build state for symptom agent
        state = {
            "symptoms": symptoms if isinstance(symptoms, list) else [symptoms],
            "duration": duration,
            "age": age,
            "severity_self_assessment": severity,
            "existing_conditions": existing_conditions,
            "current_medications": medications,
            "allergies": allergies,
            "requires_doctor": False,
            "is_emergency": False,
            "conversation_id": session_id
        }

        # Run symptom analysis agent
        result_state = await symptom_agent.ainvoke(state)

        # Also run doctor matching
        result_state = await doctor_agent.ainvoke(result_state)

        # Format response
        response = {
            "status": "success",
            "message": self._format_symptom_analysis_message(result_state),
            "analysis": {
                "severity": result_state.get("severity_classification"),
                "is_emergency": result_state.get("is_emergency", False),
                "requires_doctor": result_state.get("requires_doctor", False),
                "urgency_level": result_state.get("urgency_level", "routine"),
                "confidence_score": result_state.get("confidence_score"),
                "primary_analysis": result_state.get("primary_analysis"),
                "differential_diagnosis": result_state.get("differential_diagnosis"),
                "reasoning": result_state.get("reasoning"),
                "red_flags": result_state.get("red_flags")
            },
            "recommendations": {
                "immediate_actions": result_state.get("immediate_actions", []),
                "home_care_advice": result_state.get("home_care_advice"),
                "when_to_seek_help": result_state.get("when_to_seek_help"),
                "preparation_for_doctor": result_state.get("preparation_for_doctor")
            },
            "care_options": {
                "suggested_specialties": result_state.get("suggested_specialties"),
                "matched_doctors": result_state.get("matched_doctors", [])
            },
            "next_steps": self._get_next_steps(result_state)
        }

        return response

    def _handle_insurance_verification(self, user_input: str, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle insurance verification"""
        logger.info("Handling insurance verification request")

        provider_name = entities.get("provider_name")
        policy_number = entities.get("policy_number")
        policy_holder_name = entities.get("policy_holder_name")
        dob = entities.get("dob")

        # Check if we have required information
        required_fields = []
        if not provider_name:
            required_fields.append("provider_name")
        if not policy_number:
            required_fields.append("policy_number")
        if not policy_holder_name:
            required_fields.append("policy_holder_name")
        if not dob:
            required_fields.append("date_of_birth")

        if required_fields:
            return {
                "status": "needs_more_info",
                "message": "I can help you verify your insurance. I need a few more details:",
                "required_fields": required_fields,
                "follow_up_questions": self._generate_insurance_questions(required_fields)
            }

        # Verify insurance
        try:
            verification_result = verify_insurance(
                provider_name=provider_name,
                policy_number=policy_number,
                policy_holder_name=policy_holder_name,
                policy_holder_dob=dob,
                use_llm_detection=True
            )

            if verification_result["is_verified"]:
                message = f"✅ Great news! Your {provider_name} insurance (Policy: {policy_number}) has been successfully verified."
            else:
                message = f"❌ We encountered issues verifying your insurance. {verification_result.get('message', '')}"

            return {
                "status": "success" if verification_result["is_verified"] else "verification_failed",
                "message": message,
                "verification_result": verification_result,
                "next_steps": [
                    "You can now proceed with booking an appointment",
                    "Your insurance details have been saved to your session"
                ] if verification_result["is_verified"] else [
                    "Please double-check your policy information",
                    "Contact your insurance provider if the issue persists",
                    "You can still book an appointment without insurance verification"
                ]
            }

        except Exception as e:
            logger.error(f"Insurance verification error: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "Unable to verify insurance at this time. Please try again later.",
                "error": str(e)
            }

    def _handle_appointment_booking(self, user_input: str, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle appointment booking requests"""
        logger.info("Handling appointment booking request")

        specialty = entities.get("specialty")
        preferred_date = entities.get("preferred_date")
        doctor_name = entities.get("doctor_name")
        reason = entities.get("reason", user_input)

        # For now, provide guidance on booking
        # In a full implementation, this would integrate with the appointment scheduler
        return {
            "status": "guidance",
            "message": "I can help you book an appointment! Here's what we need:",
            "booking_flow": {
                "step": "information_gathering",
                "collected": {
                    "specialty": specialty,
                    "preferred_date": preferred_date,
                    "doctor_name": doctor_name,
                    "reason": reason
                },
                "next_questions": self._generate_booking_questions(entities)
            },
            "available_endpoints": {
                "list_doctors": "/api/v1/appointment-scheduler/doctors",
                "available_slots": "/api/v1/appointment-scheduler/slots",
                "book_appointment": "/api/v1/appointment-scheduler/book"
            },
            "instructions": [
                "1. Choose your preferred specialty or doctor",
                "2. View available time slots",
                "3. Select a slot and provide patient details",
                "4. Confirm your appointment"
            ]
        }

#     async def _handle_hospital_navigation(
#     self, 
#     user_input: str, 
#     entities: Dict[str, Any], 
#     session_id: str,
#     additional_context: Optional[Dict[str, Any]] = None
# ) -> Dict[str, Any]:
#         """Handle hospital navigation requests using the hospital guidance agent"""
#         logger.info("Handling hospital navigation request")

#         # Extract navigation-specific entities
#         location_query = entities.get("location_query", "")
#         if not location_query:
#             location_indicators = ["where is", "how do i get to", "find", "looking for", "navigate to", "directions to"]
#             for indicator in location_indicators:
#                 if indicator in user_input.lower():
#                     location_query = user_input.lower().split(indicator, 1)[1].strip().rstrip('?')
#                     break
            
#             if not location_query:
#                 location_query = user_input
        
#         # Get or create journey state
#         journey_state = self._get_journey_state(session_id)
        
#         # Determine specific intent
#         user_intent = self._map_navigation_intent(user_input, entities)
        
#         # Get current location from context or journey state
#         current_location = None
#         if additional_context and additional_context.get("current_location"):
#             current_location = additional_context.get("current_location")
#         else:
#             current_location = journey_state.get("current_location")
        
#         # Build state for hospital guidance agent
#         state = {
#             "session_id": session_id,
#             "patient_id": additional_context.get("patient_id", f"patient_{session_id}") if additional_context else f"patient_{session_id}",
#             "user_message": user_input,
#             "user_intent": user_intent, 
#             "navigation_query": location_query,
#             "current_location": current_location, 
#             "journey_stage": journey_state.get("journey_stage", JourneyStage.ARRIVAL),
#             "conversation_history": journey_state.get("conversation_history", []),
            
#             # Journey context
#             "doctor_name": additional_context.get("doctor_name", "Dr. Smith") if additional_context else "Dr. Smith",
#             "appointment_time": additional_context.get("appointment_time", datetime.now()) if additional_context else datetime.now(),
#             "reason_for_visit": additional_context.get("reason_for_visit", "Medical consultation") if additional_context else "Medical consultation",
            
#             "emergency_active": False,
#             "notifications": [],
#             "last_updated": datetime.now()
#         }

#         logger.info("Built state for hospital guidance agent: session=%s, intent=%s, query='%s'", 
#                     session_id, user_intent, location_query)
        
#         # Run hospital guidance agent
#         try:
#             result_state = await hospital_guidance_agent.ainvoke(state)
            
#             # Update journey state
#             self._update_journey_state(session_id, result_state)
            
#             # Extract the agent's message
#             agent_message = result_state.get("agent_message", "I'm here to help you navigate the hospital.")
            
#             # Build response
#             response = {
#                 "status": "success",
#                 "message": agent_message,
#                 "navigation": {
#                     "current_location": result_state.get("current_location"),
#                     "destination": result_state.get("destination"),
#                     "route": result_state.get("current_route"),
#                     "nearby_amenities": result_state.get("nearby_amenities", []),
#                     "suggested_locations": result_state.get("suggested_locations", [])
#                 },
#                 "journey": {
#                     "stage": result_state.get("journey_stage"),
#                     "queue_position": result_state.get("queue_position"),
#                     "estimated_wait": result_state.get("estimated_wait_time"),
#                 },
#                 "notifications": result_state.get("notifications", [])
#             }
            
#             return response
            
#         except Exception as e:
#             logger.error(f"Error in hospital navigation: {e}", exc_info=True)
#             return {
#                 "status": "error",
#                 "message": "I encountered an issue with navigation. Let me help you anyway - where would you like to go?",
#                 "error": str(e),
#                 "fallback_help": {
#                     "common_locations": [
#                         {"name": "Main Entrance", "building": "A", "floor": "Ground"},
#                         {"name": "Registration", "building": "A", "floor": "Ground"},
#                         {"name": "Emergency Room", "building": "A", "floor": "Ground"},
#                         {"name": "Cafeteria", "building": "A", "floor": "Ground"},
#                         {"name": "Pharmacy", "building": "A", "floor": "1"},
#                         {"name": "Laboratory", "building": "A", "floor": "2"}
#                     ]
#                 }
#             }

    async def _handle_hospital_navigation(
    self, 
    user_input: str, 
    entities: Dict[str, Any], 
    session_id: str,
    additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle hospital navigation requests using the hospital guidance agent"""
        logger.info("Handling hospital navigation request")

        # Get or create journey state
        journey_state = self._get_journey_state(session_id)
        
        # Get current location from context or journey state (with fallback to main entrance)
        current_location = None
        if additional_context and additional_context.get("current_location"):
            current_location = additional_context.get("current_location")
        elif journey_state.get("current_location"):
            current_location = journey_state.get("current_location")
        else:
            # Default to main entrance if no location provided
            current_location = {
                "building": "A",
                "building_name": "Main Building",
                "floor": "1",
                "room": "main_entrance",
                "name": "Main Entrance",
                "coordinates": {"x": 0, "y": 0}
            }
        
        # Build minimal state - let the agent decide what to do
        state = {
            "session_id": session_id,
            "patient_id": additional_context.get("patient_id", f"patient_{session_id}") if additional_context else f"patient_{session_id}",
            "user_message": user_input,
            "current_location": current_location,
            "journey_stage": journey_state.get("journey_stage", JourneyStage.ARRIVAL),
            "conversation_history": journey_state.get("conversation_history", []),
            
            # Journey context
            "doctor_name": additional_context.get("doctor_name", "Dr. Smith") if additional_context else "Dr. Smith",
            "appointment_time": additional_context.get("appointment_time", datetime.now()) if additional_context else datetime.now(),
            "reason_for_visit": additional_context.get("reason_for_visit", "Medical consultation") if additional_context else "Medical consultation",
            
            "emergency_active": False,
            "notifications": [],
            "last_updated": datetime.now()
        }

        logger.info("Invoking hospital guidance agent with message: '%s'", user_input)
        
        # Run hospital guidance agent - it will handle all the routing logic
        try:
            result_state = await hospital_guidance_agent.ainvoke(state)
            
            # Update journey state
            self._update_journey_state(session_id, result_state)
            
            # Extract the agent's message
            agent_message = result_state.get("agent_message", "I'm here to help you navigate the hospital.")
            
            # Build response
            response = {
                "status": "success",
                "message": agent_message,
                "navigation": {
                    "current_location": result_state.get("current_location"),
                    "destination": result_state.get("destination"),
                    "route": result_state.get("current_route"),
                    "nearby_amenities": result_state.get("nearby_amenities", []),
                    "suggested_locations": result_state.get("suggested_locations", [])
                },
                "journey": {
                    "stage": result_state.get("journey_stage"),
                    "queue_position": result_state.get("queue_position"),
                    "estimated_wait": result_state.get("estimated_wait_time"),
                },
                "notifications": result_state.get("notifications", [])
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error in hospital navigation: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "I encountered an issue with navigation. Let me help you anyway - where would you like to go?",
                "error": str(e),
                "fallback_help": {
                    "common_locations": [
                        {"name": "Main Entrance", "building": "A", "floor": "Ground"},
                        {"name": "Registration", "building": "A", "floor": "Ground"},
                        {"name": "Emergency Room", "building": "A", "floor": "Ground"},
                        {"name": "Cafeteria", "building": "A", "floor": "Ground"},
                        {"name": "Pharmacy", "building": "A", "floor": "1"},
                        {"name": "Laboratory", "building": "A", "floor": "2"}
                    ]
                }
            }
    
    def _map_navigation_intent(self, user_input: str, entities: Dict[str, Any]) -> str:
        """Map user input to specific navigation intent"""
        user_input_lower = user_input.lower()
        
        # Amenity search
        amenity_keywords = ["restroom", "bathroom", "toilet", "cafeteria", "cafe", "coffee", "food", "eat", "pharmacy", "gift shop"]
        if any(word in user_input_lower for word in amenity_keywords):
            return "find_amenities"
        
        # Navigation/directions
        nav_keywords = ["where is", "how do i get to", "directions to", "navigate to", "take me to", "find"]
        if any(word in user_input_lower for word in nav_keywords):
            return "navigate"
        
        # Wait time
        if any(word in user_input_lower for word in ["wait", "queue", "how long", "position"]):
            return "check_wait"
        
        # Support
        if any(word in user_input_lower for word in ["help", "lost", "confused", "don't know"]):
            return "support"
        
        return "navigate"  # Default

    def _get_journey_state(self, session_id: str) -> Dict[str, Any]:
        """Get or initialize journey state for this session"""
        if not hasattr(self, 'journey_sessions'):
            self.journey_sessions = {}
        
        if session_id not in self.journey_sessions:
            self.journey_sessions[session_id] = {
                "journey_stage": JourneyStage.ARRIVAL,
                "current_location": None,
                "conversation_history": [],
                "created_at": datetime.now().isoformat()
            }
        return self.journey_sessions[session_id]

    def _update_journey_state(self, session_id: str, result_state: Dict[str, Any]):
        """Update journey state with results from agent"""
        if not hasattr(self, 'journey_sessions'):
            self.journey_sessions = {}
        
        if session_id not in self.journey_sessions:
            self.journey_sessions[session_id] = {}
        
        # Update with relevant fields from result
        self.journey_sessions[session_id].update({
            "journey_stage": result_state.get("journey_stage"),
            "current_location": result_state.get("current_location"),
            "destination": result_state.get("destination"),
            "conversation_history": result_state.get("conversation_history", []),
            "last_updated": datetime.now().isoformat()
        })


    def _format_navigation_message(self, result_state: Dict[str, Any]) -> str:
        """Format a user-friendly navigation message"""
        route = result_state.get("current_route")
        destination = result_state.get("destination")
        
        if route and destination:
            steps_text = "\n".join([
                f"{i+1}. {step['instruction']}" 
                for i, step in enumerate(route.get("steps", []))
            ])
            
            return f"""Here's how to get to {destination['name']}:

            {steps_text}

            Estimated walking time: {route.get('estimated_time', 0) // 60} minutes
            Total distance: {route.get('distance', 0)} feet

            {self._get_accessibility_note(route)}
            """
        # Fallback message
        return result_state.get("agent_message", "I'm here to help you navigate the hospital.")

    def _get_accessibility_note(self, route: Dict[str, Any]) -> str:
        """Add accessibility information"""
        if route.get("accessible"):
            return "♿ This route is wheelchair accessible."
        return ""

    def _get_fallback_navigation_help(self, location_query: str) -> Dict[str, Any]:
        """Provide basic help when agent fails"""
        return {
            "common_locations": [
                {"name": "Main Entrance", "building": "A", "floor": "Ground"},
                {"name": "Registration", "building": "A", "floor": "Ground"},
                {"name": "Emergency Room", "building": "A", "floor": "Ground"},
                {"name": "Cafeteria", "building": "A", "floor": "Ground"},
                {"name": "Pharmacy", "building": "A", "floor": "1"}
            ],
            "help_text": "Please ask a staff member for detailed directions, or I can help you find another location."
        }

    def _handle_general_question(self, user_input: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general health questions using LLM"""
        logger.info("Handling general health question")

        prompt = f"""
You are a helpful healthcare assistant. A user has asked:

"{user_input}"

Provide a clear, accurate, and helpful response. Keep it concise (3-5 sentences).

IMPORTANT:
- Always include a disclaimer that this is general information and not medical advice
- If the question is about specific symptoms, suggest they use the symptom analysis feature
- Be supportive and empathetic

Respond in a conversational tone.
"""

        try:
            response = self.llm.invoke(prompt)
            answer = response.content

            return {
                "status": "success",
                "message": answer,
                "question": user_input,
                "disclaimer": "⚠️ This is general health information and not a substitute for professional medical advice. For specific symptoms or concerns, please consult a healthcare provider.",
                "related_features": [
                    "Need symptom analysis? Just describe your symptoms!",
                    "Want to book an appointment? Let me know!",
                    "Have insurance questions? I can help verify your coverage!"
                ]
            }

        except Exception as e:
            logger.error(f"Error answering general question: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "I'm having trouble processing your question right now. Could you try rephrasing it?",
                "error": str(e)
            }

    def _handle_unknown_intent(self, user_input: str) -> Dict[str, Any]:
        """Handle unknown or unclear intents"""
        logger.warning(f"Unknown intent for input: {user_input}")

        return {
            "status": "clarification_needed",
            "message": "I'm not quite sure what you need help with. I can assist you with:",
            "available_services": [
                "💊 Symptom Analysis - Describe your symptoms and get recommendations",
                "🏥 Insurance Verification - Verify your insurance coverage",
                "📅 Appointment Booking - Schedule appointments with doctors",
                "🧭 Hospital Navigation - Get directions within the hospital",
                "❓ General Health Questions - Ask about medical conditions, treatments, etc."
            ],
            "prompt": "What would you like help with today?"
        }

    def _format_symptom_analysis_message(self, state: Dict[str, Any]) -> str:
        """Format a user-friendly message from symptom analysis results"""
        severity = state.get("severity_classification")
        is_emergency = state.get("is_emergency", False)
        requires_doctor = state.get("requires_doctor", False)

        if is_emergency:
            return "🚨 Based on your symptoms, this may be a medical emergency. Please seek immediate medical attention!"

        if severity == "urgent_care":
            return "⚠️ Your symptoms suggest you should seek medical attention within 24 hours. Consider visiting urgent care or your doctor soon."

        if requires_doctor:
            return "📋 Based on your symptoms, I recommend scheduling an appointment with a healthcare provider within the next few days."

        return "✅ Your symptoms appear manageable with home care, but monitor them closely. Seek medical attention if they worsen."

    def _get_next_steps(self, state: Dict[str, Any]) -> List[str]:
        """Generate next steps based on symptom analysis results"""
        next_steps = []

        if state.get("matched_doctors"):
            next_steps.append("View matched doctors and book an appointment")

        if state.get("home_care_advice"):
            next_steps.append("Follow the home care recommendations provided")

        next_steps.append("Monitor your symptoms and track any changes")

        if state.get("requires_doctor"):
            next_steps.append("Schedule a doctor's appointment soon")

        return next_steps

    def _generate_insurance_questions(self, required_fields: List[str]) -> List[str]:
        """Generate follow-up questions for insurance verification"""
        questions = []

        if "provider_name" in required_fields:
            questions.append("What is your insurance provider? (e.g., Blue Cross Blue Shield, Aetna, UnitedHealthcare)")

        if "policy_number" in required_fields:
            questions.append("What is your policy/member ID number?")

        if "policy_holder_name" in required_fields:
            questions.append("What is the policy holder's full name?")

        if "date_of_birth" in required_fields:
            questions.append("What is the policy holder's date of birth? (Format: YYYY-MM-DD)")

        return questions

    def _generate_booking_questions(self, entities: Dict[str, Any]) -> List[str]:
        """Generate follow-up questions for appointment booking"""
        questions = []

        if not entities.get("specialty"):
            questions.append("Which medical specialty do you need? (e.g., Cardiology, Dermatology, General Medicine)")

        if not entities.get("preferred_date"):
            questions.append("What date would you prefer for your appointment?")

        if not entities.get("reason"):
            questions.append("What is the reason for your visit?")

        return questions

        



# Global orchestrator instance
orchestrator = HealthcareOrchestrator()
