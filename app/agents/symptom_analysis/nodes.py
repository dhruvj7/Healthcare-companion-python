from datetime import datetime
from typing import Dict, Any
from app.services.llm_service import get_llm
from langchain_core.prompts import ChatPromptTemplate

from app.agents.symptom_analysis.state import (
    SymptomAnalysisState, 
    Severity, 
    AgeGroup
)
from app.data.emergency_keywords import EMERGENCY_RED_FLAGS

import json
import re
import logging

logger = logging.getLogger(__name__)

def determine_age_group(state: SymptomAnalysisState) -> Dict[str, Any]:
    """Determine age group for age-specific guidance"""
    age = state.get('age')
    if not age:
        return state
    if age < 3:
        age_group = AgeGroup.INFANT
    elif age < 13:
        age_group = AgeGroup.CHILD
    elif age < 18:
        age_group = AgeGroup.TEEN
    elif age < 65:
        age_group = AgeGroup.ADULT
    else:
        age_group = AgeGroup.SENIOR
    
    logger.debug(f"Age group determined: {age_group} for age {age}")
    return {**state, "age_group": age_group}

def extract_symptom_keywords(state: SymptomAnalysisState) -> Dict[str, Any]:
    """Extract and normalize symptom keywords"""
    symptoms_text = ' '.join(state['symptoms']).lower()
    
    red_flags = []
    for category, flags in EMERGENCY_RED_FLAGS.items():
        for flag in flags:
            if flag in symptoms_text:
                red_flags.append(flag)
                logger.warning(f"Red flag detected: {flag}")
    
    keywords = [s.strip().lower() for s in state['symptoms']]
    
    return {
        **state,
        "symptom_keywords": keywords,
        "red_flags": red_flags,
        "timestamp": datetime.now().isoformat()
    }

def check_emergency_conditions(state: SymptomAnalysisState) -> Dict[str, Any]:
    """Rule-based emergency detection"""
    red_flags = state.get('red_flags', [])
    
    if red_flags:
        logger.critical(f"EMERGENCY detected. Red flags: {red_flags}")
        return {
            **state,
            "severity_classification": Severity.EMERGENCY,
            "is_emergency": True,
            "requires_doctor": True,
            "urgency_level": "immediate",
            "immediate_actions": [
                "CALL EMERGENCY SERVICES (911/108) IMMEDIATELY",
                "Do not drive yourself to the hospital",
                "Stay calm and follow emergency operator instructions",
                f"Critical symptoms detected: {', '.join(red_flags)}"
            ]
        }
    
    return state



def analyze_symptoms_with_llm(state: SymptomAnalysisState) -> Dict[str, Any]:
    """Deep symptom analysis using Gemini AI"""
    
    # Skip if already classified as emergency
    if state.get('is_emergency'):
        logger.info("Skipping AI analysis - already classified as emergency")
        return state
    
    logger.info("Starting AI analysis of symptoms...")
    
    # Get the LLM instance
    llm = get_llm()
    
    # Build the analysis prompt
    prompt = ChatPromptTemplate.from_template("""
You are a medical triage AI assistant. Analyze the following symptoms and provide a structured assessment.

**Patient Information:**
- Age: {age} years old ({age_group})
- Symptoms: {symptoms}
- Duration: {duration}
- Self-assessed severity (1-10): {severity_score}
- Existing conditions: {conditions}
- Current medications: {medications}
- Allergies: {allergies}

**Your Task:**
Provide a JSON response with the following structure:

{{
  "primary_analysis": "Brief clinical overview of the presentation",
  "differential_diagnosis": ["Most likely condition", "Alternative possibility 1", "Alternative possibility 2"],
  "reasoning": "Clinical reasoning for your assessment",
  "severity_assessment": "home_care|consult_doctor|urgent_care",
  "confidence_score": 0.85,
  "home_care_advice": ["Specific actionable advice 1", "Advice 2", "Advice 3"],
  "when_to_seek_help": ["Warning sign 1", "Warning sign 2"],
  "preparation_for_doctor": ["Information to track", "What to mention"]
}}

**Important Guidelines:**
1. Consider age-specific presentations (symptoms present differently in children vs adults vs elderly)
2. Account for existing conditions and medication interactions
3. Be conservative - when in doubt, recommend medical evaluation
4. Provide specific, actionable advice (not generic)
5. Consider duration and progression of symptoms
6. DO NOT diagnose - only assess severity and provide guidance
7. Focus on what the patient can do NOW

**Severity Levels Explained:**
- "home_care": Can safely manage at home with self-care
- "consult_doctor": Should schedule appointment within 2-3 days
- "urgent_care": Should seek medical attention within 24 hours

Respond ONLY with valid JSON. No markdown formatting, no explanation outside the JSON.
""")
    
    try:
        # Format the prompt with patient data
        formatted_prompt = prompt.format(
            age=state.get('age', 'Not specified'),
            age_group=state.get('age_group', AgeGroup.ADULT).value if state.get('age_group') else 'Not specified',
            symptoms=', '.join(state['symptoms']),
            duration=state.get('duration', 'Not specified'),
            severity_score=state.get('severity_self_assessment', 'Not specified'),            
            conditions=', '.join(state.get('existing_conditions') or []) or 'None',
            medications=', '.join(state.get('current_medications') or []) or 'None',
            allergies=', '.join(state.get('allergies') or []) or 'None',
        )
        
        logger.debug(f"Sending prompt to Gemini (length: {len(formatted_prompt)} chars)")
        
        # Call Gemini AI
        response = llm.invoke(formatted_prompt)
        
        logger.debug(f"Received response from Gemini (length: {len(response.content)} chars)")
        
        # Parse the JSON response
        content = response.content.strip()
        
        # Remove markdown code blocks if Gemini added them
        # Sometimes AI returns: ```json\n{...}\n```
        content = re.sub(r'^```json\s*|\s*```$', '', content, flags=re.MULTILINE)
        
        # Parse JSON
        result = json.loads(content)
        
        logger.info(f"AI analysis complete - Severity: {result.get('severity_assessment')}")
        
        # Map severity string to our Enum
        severity_map = {
            "home_care": Severity.HOME_CARE,
            "consult_doctor": Severity.CONSULT_DOCTOR,
            "urgent_care": Severity.URGENT_CARE
        }
        
        severity = severity_map.get(
            result.get('severity_assessment'), 
            Severity.CONSULT_DOCTOR  # Default to consult_doctor if unclear
        )
        
        # Update state with AI analysis results
        return {
            **state,
            "primary_analysis": result.get('primary_analysis'),
            "differential_diagnosis": result.get('differential_diagnosis', []),
            "reasoning": result.get('reasoning'),
            "severity_classification": severity,
            "confidence_score": result.get('confidence_score', 0.7),
            "home_care_advice": result.get('home_care_advice', []),
            "when_to_seek_help": result.get('when_to_seek_help', []),
            "preparation_for_doctor": result.get('preparation_for_doctor', [])
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response as JSON: {str(e)}")
        logger.error(f"Raw response: {content}")
        # Fallback to safe default
        return fallback_analysis(state)
        
    except Exception as e:
        logger.error(f"Error during AI analysis: {str(e)}", exc_info=True)
        # Fallback to safe default
        return fallback_analysis(state)


def fallback_analysis(state: SymptomAnalysisState) -> Dict[str, Any]:
    """Conservative fallback when AI fails"""
    logger.warning("Using fallback analysis due to AI error")
    
    return {
        **state,
        "severity_classification": Severity.CONSULT_DOCTOR,
        "requires_doctor": True,
        "confidence_score": 0.5,
        "primary_analysis": "Unable to complete AI analysis. Please consult a healthcare provider for proper evaluation.",
        "immediate_actions": [
            "Schedule an appointment with your healthcare provider",
            "Monitor your symptoms closely",
            "Seek immediate care if symptoms worsen"
        ]
    }


def finalize_recommendations(state: SymptomAnalysisState) -> Dict[str, Any]:
    """Generate final recommendations based on classification"""
    
    severity = state.get('severity_classification')
    
    # If already handled as emergency, just return
    if state.get('is_emergency'):
        logger.info("Emergency case - recommendations already set")
        return state
    
    # Handle based on severity level
    if severity == Severity.URGENT_CARE:
        logger.info("Finalizing URGENT_CARE recommendations")
        return {
            **state,
            "requires_doctor": True,
            "urgency_level": "within_24hrs",
            "immediate_actions": [
                "⚠️ Seek medical attention within 24 hours",
                "Visit urgent care or emergency room if symptoms worsen",
                "Monitor symptoms closely for any changes",
                "Have someone available to drive you if needed"
            ]
        }
    
    elif severity == Severity.CONSULT_DOCTOR:
        logger.info("Finalizing CONSULT_DOCTOR recommendations")
        return {
            **state,
            "requires_doctor": True,
            "urgency_level": "within_week",
            "immediate_actions": [
                "📞 Schedule an appointment with your doctor within 2-3 days",
                "Keep track of symptom changes (write them down)",
                "Prepare information for your doctor visit (see preparation section below)",
                "Continue any current medications as prescribed"
            ]
        }
    
    else:  # HOME_CARE
        logger.info("Finalizing HOME_CARE recommendations")
        return {
            **state,
            "requires_doctor": False,
            "urgency_level": "monitor",
            "immediate_actions": [
                "✅ Symptoms can likely be managed at home",
                "Follow home care recommendations below carefully",
                "Monitor symptoms daily for any worsening",
                "Seek medical attention if symptoms worsen or new symptoms develop (see warning signs below)"
            ]
        }