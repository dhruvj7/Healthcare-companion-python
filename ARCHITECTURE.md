# Healthcare Companion - System Architecture

## 🏗️ Architecture Overview

This is an **AI-powered healthcare orchestration system** that automatically routes user requests to specialized agents based on intent classification.

---

## 📐 System Components

### 1. **Intent Classification Layer** 🧠

**File:** `app/services/intent_classifier.py`

**Purpose:** Automatically determine what the user needs

**How it works:**
- Uses **Gemini LLM** to classify user input
- Extracts relevant entities (symptoms, insurance details, etc.)
- Falls back to **rule-based classification** if LLM fails
- Returns confidence score and reasoning

**Supported Intents:**
```python
class IntentType(Enum):
    SYMPTOM_ANALYSIS = "symptom_analysis"
    INSURANCE_VERIFICATION = "insurance_verification"
    APPOINTMENT_BOOKING = "appointment_booking"
    HOSPITAL_NAVIGATION = "hospital_navigation"
    GENERAL_HEALTH_QUESTION = "general_health_question"
    EMERGENCY = "emergency"
    UNKNOWN = "unknown"
```

---

### 2. **Orchestrator Agent** 🎯

**File:** `app/agents/orchestrator/agent.py`

**Purpose:** Route requests to appropriate specialized agents

**Flow:**
```
User Input
    ↓
Classify Intent (LLM)
    ↓
Route to Agent based on Intent
    ↓
    ├─ EMERGENCY → Immediate response
    ├─ SYMPTOM_ANALYSIS → Symptom Agent → Doctor Matching
    ├─ INSURANCE_VERIFICATION → Insurance Verifier → CSV Lookup
    ├─ APPOINTMENT_BOOKING → Appointment Scheduler
    ├─ HOSPITAL_NAVIGATION → Navigation Tools
    └─ GENERAL_HEALTH_QUESTION → LLM Q&A
    ↓
Format Unified Response
    ↓
Return to User
```

**Key Features:**
- **Session Management:** Tracks conversation history
- **Context Awareness:** Uses previous messages for better classification
- **Graceful Fallback:** Handles unknown intents elegantly
- **Entity Extraction:** Pulls out key information from user input

---

### 3. **Specialized Agents** 🤖

#### A. **Symptom Analysis Agent**
- **Location:** `app/agents/symptom_analysis/`
- **Technology:** LangGraph state machine
- **Features:**
  - Emergency detection (rule-based red flags)
  - AI-powered symptom analysis with Gemini
  - Age-specific recommendations
  - Differential diagnosis
  - Home care advice

#### B. **Doctor Finder Agent**
- **Location:** `app/agents/doctor_finder/`
- **Technology:** Hybrid LLM + rule-based matching
- **Features:**
  - Specialty resolution from symptoms
  - Doctor database matching
  - Emergency support filtering

#### C. **Insurance Verifier**
- **Location:** `app/services/insurance_verifier.py`
- **Technology:** CSV-based verification + LLM provider detection
- **Features:**
  - Intelligent provider name matching
  - Policy validation against CSV database
  - Detailed error reporting

#### D. **Appointment Scheduler**
- **Location:** `app/agents/appointment_scheduler/`
- **Technology:** SQLite database
- **Features:**
  - Doctor and slot management
  - Email confirmations (HTML templates)
  - Booking workflow

#### E. **Hospital Guidance Agent**
- **Location:** `app/agents/hospital_guidance/`
- **Technology:** Complex LangGraph state machine
- **Features:**
  - Multi-stage journey management (arrival → departure)
  - Navigation and wayfinding
  - Queue management
  - Visit assistance
  - Emergency handling

---

### 4. **Unified API Endpoint** 🌐

**File:** `app/api/v1/routes/unified_chat.py`

**Endpoint:** `POST /api/v1/public/chat`

**Request:**
```json
{
  "message": "I have a fever and cough",
  "session_id": "session_abc123",  // optional
  "context": {}  // optional
}
```

**Response:**
```json
{
  "session_id": "session_abc123",
  "timestamp": "2026-02-08T10:30:00",
  "user_input": "I have a fever and cough",
  "intent": "symptom_analysis",
  "confidence": 0.95,
  "reasoning": "User is describing symptoms...",
  "requires_more_info": true,
  "follow_up_questions": ["How old are you?"],
  "result": {
    "status": "success",
    "message": "Based on your symptoms...",
    "analysis": { ... },
    "recommendations": { ... }
  }
}
```

---

### 5. **Angular Frontend** 💻

**Location:** `frontend/angular/`

**Components:**
- **ChatComponent:** Main UI for conversation
- **ChatService:** HTTP communication with backend
- **Models:** TypeScript interfaces for type safety

**Features:**
- Real-time chat interface
- Intent visualization
- Session management
- Markdown rendering
- Loading states
- Error handling
- Responsive design

---

## 🔄 Request Flow Example

### Example: "I have a fever and cough for 3 days"

```
1. USER TYPES MESSAGE
   ↓
2. ANGULAR UI
   - ChatService.sendMessage()
   - POST /api/v1/public/chat
   ↓
3. UNIFIED API ENDPOINT
   - Receives request
   - Passes to Orchestrator
   ↓
4. INTENT CLASSIFIER (LLM)
   - Analyzes: "I have a fever and cough for 3 days"
   - Classifies: SYMPTOM_ANALYSIS
   - Confidence: 0.95
   - Extracts: { symptoms: ["fever", "cough"], duration: "3 days" }
   ↓
5. ORCHESTRATOR ROUTER
   - Routes to: _handle_symptom_analysis()
   - Builds state for symptom agent
   ↓
6. SYMPTOM ANALYSIS AGENT (LangGraph)
   - Node 1: determine_age_group
   - Node 2: extract_symptom_keywords
   - Node 3: check_emergency_conditions (✅ No emergency)
   - Node 4: analyze_symptoms_with_llm (Gemini AI)
   - Node 5: finalize_recommendations
   ↓
7. DOCTOR FINDER AGENT
   - Resolves specialty: "General Medicine"
   - Matches doctors from database
   ↓
8. FORMAT RESPONSE
   - Status: success
   - Message: "Based on your symptoms..."
   - Analysis: { severity, diagnosis, etc. }
   - Recommendations: { immediate_actions, home_care, etc. }
   - Matched doctors: [...]
   ↓
9. RETURN TO USER
   - JSON response to Angular
   - Display in chat UI
   - Show intent badge
   - Save to conversation history
```

---

## 🔐 Security Considerations

### Current Implementation
- **Session-based:** In-memory session storage
- **CORS:** Configured in `config.py`
- **Input Validation:** Pydantic models
- **Error Handling:** No sensitive data in error messages

### Production Recommendations
- [ ] Add authentication (JWT tokens)
- [ ] Use Redis for session storage
- [ ] Implement rate limiting
- [ ] Add request logging and monitoring
- [ ] Encrypt sensitive data (insurance info)
- [ ] Use HTTPS only
- [ ] Implement API key rotation for Gemini

---

## 📊 Database Schema

### SQLite (Appointments)

**Tables:**
- `doctors` - Doctor information
- `available_slots` - Appointment slots
- `appointments` - Booked appointments

### CSV Files (Insurance)

**Location:** `app/data/insurance/*.csv`

**Format:**
```csv
policy_number,policy_holder_name,policy_holder_dob,status,coverage_type,copay_amount,effective_date,expiration_date
ABC123456,John Doe,1985-05-15,active,PPO,45,2025-01-01,2026-12-31
```

**Supported Providers:**
- Blue Cross Blue Shield
- Aetna
- United Healthcare
- Cigna
- Humana
- Kaiser Permanente
- Anthem
- Medicare
- Medicaid

---

## 🎯 Intent Classification Details

### LLM Prompt Engineering

The classifier uses a carefully crafted prompt that:
1. **Describes all available intents** with examples
2. **Requests JSON output** with specific schema
3. **Asks for entity extraction** from user input
4. **Requests confidence score** and reasoning
5. **Identifies follow-up questions** if needed

### Fallback Rules

If LLM fails, rule-based classification uses:
- **Keyword matching** for each intent
- **Emergency keyword detection** (highest priority)
- **Confidence scoring** based on match strength

---

## 🚀 Performance Optimization

### Current Setup
- **LLM Model:** Gemini 2.5 Flash (fast, cheap)
- **Temperature:** 0.3 (deterministic)
- **Max Tokens:** 2048
- **Session Storage:** In-memory (fast, limited)

### Optimization Opportunities
1. **Cache LLM responses** for common queries
2. **Use Gemini 1.5 Flash** for even faster responses
3. **Implement request batching** for multiple agents
4. **Add Redis** for session persistence
5. **Lazy load agent modules** to reduce startup time

---

## 📈 Scalability

### Vertical Scaling
- Increase server resources (CPU, RAM)
- Use faster LLM models
- Optimize database queries

### Horizontal Scaling
- Deploy multiple backend instances
- Use load balancer (Nginx, AWS ALB)
- Shared session store (Redis)
- Database replication

---

## 🧪 Testing Strategy

### Unit Tests
```python
# Test intent classification
def test_intent_classifier():
    result = classify_intent("I have a fever")
    assert result.intent == IntentType.SYMPTOM_ANALYSIS
    assert result.confidence > 0.7

# Test orchestrator routing
def test_orchestrator_symptom():
    response = orchestrator.process_request("I have chest pain")
    assert response['intent'] == 'symptom_analysis'
    assert 'analysis' in response['result']
```

### Integration Tests
```python
# Test full flow via API
def test_chat_endpoint():
    response = client.post("/api/v1/public/chat", json={
        "message": "I have a fever"
    })
    assert response.status_code == 200
    assert response.json()['intent'] == 'symptom_analysis'
```

### E2E Tests (Angular)
```typescript
// Test chat UI
it('should send message and display response', () => {
  // Type message
  component.userInput = 'I have a fever';

  // Send
  component.sendMessage();

  // Verify API call
  expect(chatService.sendMessage).toHaveBeenCalled();

  // Verify response displayed
  expect(component.messages.length).toBeGreaterThan(1);
});
```

---

## 🔧 Configuration

### Environment Variables

```env
# Required
GOOGLE_API_KEY=your_key_here

# Optional (with defaults)
LLM_MODEL=gemini-2.5-flash
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048
LOG_LEVEL=INFO
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### Frontend Configuration

```typescript
// src/environments/environment.ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
```

---

## 📚 Key Algorithms

### Intent Classification Algorithm

```
1. Accept user input + conversation history
2. Build context-aware prompt for LLM
3. Request structured JSON with:
   - intent classification
   - entity extraction
   - confidence score
   - follow-up questions
4. Parse LLM response
5. If parsing fails → fallback to rules
6. If confidence < 0.6 → also try rules
7. Return highest confidence result
```

### Entity Extraction Algorithm

```
1. LLM extracts entities based on intent:
   - Symptoms → list of symptoms, duration, severity
   - Insurance → provider, policy number, holder name
   - Appointment → specialty, date, reason
   - Navigation → location query, destination
2. Store in extracted_entities dict
3. Check for missing required fields
4. Generate follow-up questions if incomplete
```

---

## 🎨 UI/UX Design Principles

1. **Conversational:** Natural chat-like interface
2. **Transparent:** Show intent and confidence
3. **Helpful:** Provide example prompts
4. **Responsive:** Real-time feedback with loading states
5. **Accessible:** Keyboard navigation, clear labels
6. **Forgiving:** Clear error messages, easy recovery

---

## 🔮 Future Enhancements

### Short-term
- [ ] Voice input/output
- [ ] Multi-language support
- [ ] User authentication
- [ ] Conversation export (PDF)
- [ ] Admin dashboard

### Long-term
- [ ] Telemedicine video integration
- [ ] Prescription ordering
- [ ] Lab result integration
- [ ] Wearable device data
- [ ] Predictive health analytics

---

## 📞 API Reference Quick Guide

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/public/chat` | POST | Main unified endpoint |
| `/api/v1/chat/conversation/{id}` | GET | Get chat history |
| `/api/v1/chat/conversation/{id}` | DELETE | Clear history |
| `/api/v1/chat/capabilities` | GET | Get system capabilities |
| `/api/v1/chat/health` | GET | Health check |

---

**Built with ❤️ using FastAPI, LangGraph, Gemini AI, and Angular**
