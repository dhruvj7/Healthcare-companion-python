# app/agents/orchestrator/agent.py

"""
Unified Orchestrator Agent

Routes user requests to appropriate specialized agents based on intent classification.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.agents.appointment_scheduler.node import appointment_booking_node
from app.services.intent_classifier import classify_intent, IntentType
from app.agents.symptom_analysis.agent import symptom_agent
from app.agents.doctor_finder.agent import doctor_agent
from app.services.llm_service import get_llm
from app.services.insurance_verifier import verify_insurance
from app.agents.appointment_scheduler.crud import get_available_slots, book_appointment

logger = logging.getLogger(__name__)


class HealthcareOrchestrator:
    """
    Main orchestrator that handles all user requests and routes to appropriate agents.
    """

    def __init__(self):
        self.llm = get_llm()
        self.conversation_sessions: Dict[str, List[Dict[str, Any]]] = {}

    async def process_request(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        booking_slot_id:Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for processing user requests.

        Args:
            user_input: The user's message/prompt
            session_id: Optional session ID for conversation continuity
            additional_context: Optional additional context (user profile, location, etc.)
            booking_slot_id: Optional booking slot ID for appointment booking

        Returns:
            Unified response with results from appropriate agent
        """
        logger.info(f"Processing request: '{user_input[:100]}...'")

        # Generate or use existing session ID
        if not session_id:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
            logger.info(f"Created new session: {session_id}")

        # Get conversation history
        conversation_history = self.conversation_sessions.get(session_id, [])

        # Step 1: Classify Intent
        classification = classify_intent(user_input, conversation_history)

        logger.info(f"Intent: {classification.intent.value} (confidence: {classification.confidence})")

        # Store user message in history
        conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"booking slot received in orchestrator: {booking_slot_id}")

        # Step 2: Route to Appropriate Agent
        result = await self._route_to_agent(
            intent=classification.intent,
            user_input=user_input,
            extracted_entities=classification.extracted_entities,
            session_id=session_id,
            additional_context=additional_context or {},
            booking_slot_id=booking_slot_id or None
        )

        # Step 3: Build Unified Response
        response = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "intent": classification.intent.value,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning,
            "requires_more_info": classification.requires_more_info,
            "follow_up_questions": classification.follow_up_questions,
            "result": result
        }

        # Store assistant response in history
        conversation_history.append({
            "role": "assistant",
            "content": result.get("message", ""),
            "intent": classification.intent.value,
            "timestamp": datetime.now().isoformat()
        })

        # Update conversation history (keep last 20 messages)
        self.conversation_sessions[session_id] = conversation_history[-20:]

        return response

    async def _route_to_agent(
        self,
        intent: IntentType,
        user_input: str,
        extracted_entities: Dict[str, Any],
        session_id: str,
        additional_context: Dict[str, Any],
        booking_slot_id: Optional[int]
    ) -> Dict[str, Any]:
        """
        Route request to the appropriate specialized agent.

        Args:
            intent: Classified intent
            user_input: Original user input
            extracted_entities: Extracted information from user input
            session_id: Session identifier
            additional_context: Additional context

        Returns:
            Agent-specific response
        """
        logger.info(f"Routing to agent for intent: {intent.value}")

        try:
            if intent == IntentType.EMERGENCY:
                return self._handle_emergency(user_input, extracted_entities)

            elif intent == IntentType.SYMPTOM_ANALYSIS:
                return await self._handle_symptom_analysis(user_input, extracted_entities, session_id)

            elif intent == IntentType.INSURANCE_VERIFICATION:
                return self._handle_insurance_verification(user_input, extracted_entities, session_id)

            elif intent == IntentType.APPOINTMENT_BOOKING:
                return await self._handle_appointment_booking(user_input, slot_id=booking_slot_id, entities=extracted_entities, session_id=session_id)

            elif intent == IntentType.HOSPITAL_NAVIGATION:
                return self._handle_hospital_navigation(user_input, extracted_entities, session_id)

            elif intent == IntentType.GENERAL_HEALTH_QUESTION:
                return self._handle_general_question(user_input, extracted_entities)

            else:
                return self._handle_unknown_intent(user_input)

        except Exception as e:
            logger.error(f"Error routing to agent: {e}", exc_info=True)
            return {
                "status": "error",
                "message": "An error occurred while processing your request. Please try again.",
                "error": str(e)
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
                "matched_doctors": result_state.get("matched_doctors", []),
                "available_slots": result_state.get("available_appointments", {})
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

    async def _handle_appointment_booking(self, user_input: str, slot_id: int, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle appointment booking requests"""
        logger.info("Handling appointment booking request")
        logger.info(f"Entities received: {entities}")

        # Extract booking-related entities
        slot_id = slot_id
        patient_name = entities.get("patient_name")
        patient_email = entities.get("patient_email")
        patient_phone = entities.get("patient_phone")
        reason_for_visit = entities.get("reason_for_visit") or entities.get("reason", user_input)
        appointment_type = entities.get("appointment_type", "in-person")

        logger.info("entities extracted for booking")

        # Check if we have all required information to proceed with booking
        if all([slot_id, patient_name, patient_email, patient_phone]):
            logger.info(f"All booking fields present - proceeding with appointment booking for slot {slot_id}")

            # Build state for booking node
            booking_state = {
                "slot_id": slot_id,
                "patient_name": patient_name,
                "patient_email": patient_email,
                "patient_phone": patient_phone,
                "reason_for_visit": reason_for_visit,
                "appointment_type": appointment_type,
                "session_id": session_id
            }

            logger.info("Booking state constructed")

            # Call appointment booking node
            result_state = await appointment_booking_node(booking_state)

            # Format response based on booking status
            if result_state.get("booking_status") == "confirmed":
                return {
                    "status": "success",
                    "message": result_state.get("confirmation_message"),
                    "booking_details": result_state.get("appointment_details"),
                    "booking_id": result_state.get("booking_id"),
                    "emails_sent": result_state.get("emails_sent", False)
                }
            else:
                return {
                    "status": "error",
                    "message": result_state.get("confirmation_message"),
                    "error": result_state.get("error"),
                    "next_steps": [
                        "Please verify the slot is still available",
                        "Check that all information is correct",
                        "Try selecting a different time slot if needed"
                    ]
                }

        # If missing required fields, provide guidance
        specialty = entities.get("specialty")
        preferred_date = entities.get("preferred_date")
        doctor_name = entities.get("doctor_name")

        required_fields = []
        if not slot_id:
            required_fields.append("slot_id")
        if not patient_name:
            required_fields.append("patient_name")
        if not patient_email:
            required_fields.append("patient_email")
        if not patient_phone:
            required_fields.append("patient_phone")

        return {
            "status": "needs_more_info",
            "message": "I can help you book an appointment! Let me gather the necessary information.",
            "required_fields": required_fields,
            "booking_flow": {
                "step": "information_gathering",
                "collected": {
                    "slot_id": slot_id,
                    "patient_name": patient_name,
                    "patient_email": patient_email,
                    "patient_phone": patient_phone,
                    "specialty": specialty,
                    "preferred_date": preferred_date,
                    "doctor_name": doctor_name,
                    "reason": reason_for_visit
                },
                "next_questions": self._generate_booking_questions(entities)
            },
            "instructions": [
                "1. Choose your preferred specialty or doctor",
                "2. View available time slots",
                "3. Provide your personal details (name, email, phone)",
                "4. Confirm your appointment"
            ]
        }        

    def _handle_hospital_navigation(self, user_input: str, entities: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """Handle hospital navigation requests"""
        logger.info("Handling hospital navigation request")

        location_query = entities.get("location_query", user_input)

        return {
            "status": "guidance",
            "message": f"I can help you navigate the hospital. You're looking for: {location_query}",
            "navigation_info": {
                "query": location_query,
                "guidance": "To use the full navigation system, please initialize a hospital journey session.",
                "endpoint": "/api/v1/hospital-guidance/initialize"
            },
            "quick_help": {
                "common_locations": [
                    {"name": "Main Entrance", "building": "A", "floor": "Ground"},
                    {"name": "Emergency Room", "building": "A", "floor": "Ground"},
                    {"name": "Cafeteria", "building": "B", "floor": "1"},
                    {"name": "Pharmacy", "building": "A", "floor": "1"},
                    {"name": "Restrooms", "location": "Available on every floor"}
                ]
            }
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
            next_steps.append("Schedule a doctor's appointment soon.")
            next_steps.append("To book an appointment, choose the preferred slot, mention your name, email, phone and appointment type.")

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
