# app/api/v1/routes/unified_chat.py

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.agents.orchestrator import orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()


# ===== REQUEST/RESPONSE MODELS =====

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User's message/prompt", min_length=1)
    session_id: Optional[str] = Field(default=None)#, description="Session ID for conversation continuity")
    context: Optional[Dict[str, Any]] = Field(default=None)#, description="Additional context (user profile, location, etc.)")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "I have a fever and cough for 3 days",
                "session_id": "session_abc123",
                "context": {
                    "user_age": 35,
                    "location": "hospital_lobby"
                }
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    user_input: str = Field(..., description="Original user input")
    intent: List[str]=Field(...,description="intent")

    confidence: float = Field(..., description="Intent classification confidence (0-1)")
    reasoning: str = Field(..., description="Why this intent was chosen")
    requires_more_info: bool = Field(..., description="Whether more information is needed")
    follow_up_questions: List[str] = Field(default_factory=list, description="Questions to ask user")
    result: Dict[str, Any] = Field(..., description="Result from the selected agent/tool")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_abc123",
                "timestamp": "2026-02-08T10:30:00",
                "user_input": "I have a fever and cough",
                "intent": "symptom_analysis",
                "confidence": 0.95,
                "reasoning": "User is describing specific symptoms that need medical analysis",
                "requires_more_info": True,
                "follow_up_questions": ["How old are you?", "Do you have any existing conditions?"],
                "result": {
                    "status": "success",
                    "message": "Based on your symptoms...",
                    "analysis": {}
                }
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history"""
    session_id: str
    messages: List[Dict[str, Any]]
    message_count: int


# ===== ENDPOINTS =====


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def unified_chat(request: ChatRequest):
    try:
        logger.info(f"Received chat request: '{request.message[:100]}...'")

        result = await orchestrator.process_request(
            user_input=request.message,
            session_id=request.session_id,
            additional_context=request.context
        )

        # ================================
        # ✅ MULTI-INTENT HANDLING LOGIC
        # ================================

        # If new multi-intent response
        if "intents" in result:
            intents = result.get("intents", [])
            # primary_intent = intents[0] if intents else "unknown"

            requires_more_info = False
            follow_up_questions = []

            # If multi-intent result
            if result.get("result", {}).get("status") == "multi_intent_success":
                sub_results = result["result"].get("sub_results", [])

                # Merge sub results cleanly
                merged_result = {
                    "status": "multi_intent_success",
                    "message": result["result"].get("message"),
                    "sub_results": sub_results
                }

                return ChatResponse(
                    session_id=result["session_id"],
                    timestamp=result["timestamp"],
                    user_input=result["user_input"],
                    intent=intents,
                    confidence=result.get("confidence", 0.8),
                    reasoning=result.get("reasoning", "Multi-intent classification"),
                    requires_more_info=requires_more_info,
                    follow_up_questions=follow_up_questions,
                    result=merged_result
                )

            # Single intent but returned as list
            return ChatResponse(
                session_id=result["session_id"],
                timestamp=result["timestamp"],
                user_input=result["user_input"],
                intent=intents,
                confidence=result.get("confidence", 0.8),
                reasoning=result.get("reasoning", ""),
                requires_more_info=result.get("requires_more_info", False),
                follow_up_questions=result.get("follow_up_questions", []),
                result=result.get("result", {})
            )

        # ================================
        # ✅ BACKWARD COMPATIBILITY
        # ================================

        logger.info(f"Request processed successfully. Intent: {result['intent']}")

        return ChatResponse(**result)

    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process your request: {str(e)}"
        )


@router.get("/conversation/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str):
    """
    **Get Conversation History**

    Retrieve the conversation history for a specific session.

    **Parameters:**
    - `session_id`: The session identifier

    **Response:**
    Returns all messages in the conversation with timestamps and intents.

    **Example:**
    ```
    GET /api/v1/chat/conversation/session_abc123
    ```
    """
    try:
        logger.info(f"Retrieving conversation history for session: {session_id}")

        # Get conversation from orchestrator
        conversation = orchestrator.conversation_sessions.get(session_id, [])

        if not conversation:
            logger.warning(f"No conversation found for session: {session_id}")
            return ConversationHistoryResponse(
                session_id=session_id,
                messages=[],
                message_count=0
            )

        return ConversationHistoryResponse(
            session_id=session_id,
            messages=conversation,
            message_count=len(conversation)
        )

    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@router.delete("/conversation/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_conversation(session_id: str):
    """
    **Clear Conversation History**

    Delete the conversation history for a specific session.

    **Parameters:**
    - `session_id`: The session identifier

    **Example:**
    ```
    DELETE /api/v1/public/conversation/session_abc123
    ```
    """
    try:
        logger.info(f"Clearing conversation history for session: {session_id}")

        if session_id in orchestrator.conversation_sessions:
            del orchestrator.conversation_sessions[session_id]
            logger.info(f"Conversation cleared for session: {session_id}")
        else:
            logger.warning(f"No conversation found for session: {session_id}")

        return None

    except Exception as e:
        logger.error(f"Error clearing conversation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear conversation: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    **Health Check**

    Simple endpoint to check if the chat service is running.
    """
    return {
        "status": "healthy",
        "service": "unified-chat",
        "timestamp": datetime.now().isoformat(),
        "orchestrator_sessions": len(orchestrator.conversation_sessions)
    }


@router.get("/capabilities")
async def get_capabilities():
    """
    **Get System Capabilities**

    Returns information about what the system can do.

    Useful for displaying help text or capability cards in the UI.
    """
    return {
        "capabilities": [
            {
                "name": "Symptom Analysis",
                "intent": "symptom_analysis",
                "description": "Analyze your symptoms and get medical recommendations",
                "example": "I have a fever and cough for 3 days",
                "icon": "💊"
            },
            {
                "name": "Insurance Verification",
                "intent": "insurance_verification",
                "description": "Verify your insurance coverage and policy details",
                "example": "Verify my Blue Cross insurance policy ABC123",
                "icon": "🏥"
            },
            {
                "name": "Appointment Booking",
                "intent": "appointment_booking",
                "description": "Schedule appointments with healthcare providers",
                "example": "Book appointment with cardiologist next Tuesday",
                "icon": "📅"
            },
            {
                "name": "Hospital Navigation",
                "intent": "hospital_navigation",
                "description": "Get directions and find amenities in the hospital",
                "example": "Where is the cafeteria?",
                "icon": "🧭"
            },
            {
                "name": "General Health Questions",
                "intent": "general_health_question",
                "description": "Ask questions about medical conditions and health topics",
                "example": "What is high blood pressure?",
                "icon": "❓"
            },
            {
                "name": "Emergency Detection",
                "intent": "emergency",
                "description": "Automatic detection of medical emergencies",
                "example": "Severe chest pain and difficulty breathing",
                "icon": "🚨"
            }
        ],
        "notes": [
            "Just type naturally - the system will understand your intent",
            "You can ask follow-up questions in the same conversation",
            "Emergency situations are automatically detected and prioritized"
        ]
    }
