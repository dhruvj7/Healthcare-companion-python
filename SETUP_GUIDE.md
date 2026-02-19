# Healthcare Companion - Complete Setup Guide

This guide will help you set up both the backend (Python/FastAPI) and frontend (Angular) for the Healthcare Companion application.

---

## 🚀 Quick Start

### Backend Setup (Python/FastAPI)

1. **Navigate to project directory**
   ```bash
   cd Healthcare-companion-python
   ```

2. **Create and activate virtual environment**
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux/Mac
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the root directory:
   ```env
   # Google Gemini API
   GOOGLE_API_KEY=your_google_api_key_here

   # Server Config
   DEBUG=True
   HOST=0.0.0.0
   PORT=8000

   # LLM Config
   LLM_MODEL=gemini-2.5-flash
   LLM_TEMPERATURE=0.3
   LLM_MAX_TOKENS=2048

   # Email Config (Optional)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   SMTP_FROM_EMAIL=your_email@gmail.com

   # Logging
   LOG_LEVEL=INFO
   ```

5. **Create insurance CSV files directory**
   ```bash
   mkdir -p app/data/insurance
   ```

6. **Run the backend server**
   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at: `http://localhost:8000`

   API Documentation: `http://localhost:8000/docs`

---

### Frontend Setup (Angular)

1. **Navigate to frontend directory**
   ```bash
   cd frontend/angular
   ```

2. **Install Node.js dependencies**
   ```bash
   npm install
   ```

   If you don't have Angular CLI installed globally:
   ```bash
   npm install -g @angular/cli
   ```

3. **Update environment configuration** (if needed)

   Edit `src/environments/environment.ts`:
   ```typescript
   export const environment = {
     production: false,
     apiUrl: 'http://localhost:8000/api/v1'
   };
   ```

4. **Start the development server**
   ```bash
   ng serve
   ```

   or

   ```bash
   npm start
   ```

   The UI will be available at: `http://localhost:4200`

---

## 📝 Usage

### Testing the Unified Chat API

**Option 1: Using the Angular UI**

1. Open browser: `http://localhost:4200`
2. Type any message in the chat interface
3. The AI will automatically:
   - Classify your intent
   - Route to the appropriate agent
   - Return a processed response

**Option 2: Using cURL**

```bash
# Symptom Analysis Example
curl -X POST http://localhost:8000/api/v1/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have a fever and cough for 3 days"
  }'

# Insurance Verification Example
curl -X POST http://localhost:8000/api/v1/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Verify my Blue Cross insurance policy ABC123456",
    "session_id": "session_123"
  }'

# General Health Question
curl -X POST http://localhost:8000/api/v1/public/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is diabetes?"
  }'
```

**Option 3: Using Python requests**

```python
import requests

# Send a message
response = requests.post(
    'http://localhost:8000/api/v1/public/chat',
    json={
        'message': 'I have chest pain and shortness of breath'
    }
)

result = response.json()
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']}")
print(f"Response: {result['result']['message']}")
```

---

## 🎯 Example User Inputs

The system automatically detects intent from these types of messages:

### 💊 Symptom Analysis
- "I have a fever and cough for 3 days"
- "My head hurts and I feel dizzy"
- "Chest pain and difficulty breathing"
- "Severe stomach pain, nausea, and vomiting"

### 🏥 Insurance Verification
- "Verify my Blue Cross insurance"
- "Check my Aetna policy number ABC123456"
- "I want to verify my insurance with UnitedHealthcare"
- "My insurance provider is Cigna, policy ABC123"

### 📅 Appointment Booking
- "Book appointment with cardiologist"
- "Schedule checkup next Tuesday"
- "I need to see a dermatologist this week"
- "Find me a doctor for diabetes management"

### 🧭 Hospital Navigation
- "Where is the cafeteria?"
- "How do I get to the radiology department?"
- "Find the nearest restroom"
- "What's my queue position?"

### ❓ General Health Questions
- "What is diabetes?"
- "How do I lower my blood pressure?"
- "Explain what cholesterol means"
- "What causes migraines?"

### 🚨 Emergency Detection
- "Severe chest pain and can't breathe"
- "Someone collapsed and is unconscious"
- "Heavy bleeding that won't stop"
- "Severe allergic reaction, throat swelling"

---

## 🔧 API Endpoints

### Unified Chat API (Main Entry Point)

**POST** `/api/v1/public/chat`
- Main endpoint for all interactions
- Automatically routes to appropriate agent

**GET** `/api/v1/chat/conversation/{session_id}`
- Retrieve conversation history

**DELETE** `/api/v1/chat/conversation/{session_id}`
- Clear conversation

**GET** `/api/v1/chat/capabilities`
- Get system capabilities

### Legacy Endpoints (Still Available)

These are the original specialized endpoints that the orchestrator uses internally:

- `/api/v1/analyze-symptoms` - Direct symptom analysis
- `/api/v1/appointment-scheduler/*` - Direct appointment booking
- `/api/v1/hospital-guidance/*` - Direct hospital navigation
- `/api/v1/insurance/*` - Direct insurance verification

---

## 🧪 Testing the Intent Classification

You can test the intent classifier independently:

```python
from app.services.intent_classifier import classify_intent

# Test different inputs
inputs = [
    "I have a fever",
    "Verify my insurance",
    "Book appointment",
    "Where is the cafeteria?"
]

for user_input in inputs:
    result = classify_intent(user_input)
    print(f"Input: {user_input}")
    print(f"Intent: {result.intent.value}")
    print(f"Confidence: {result.confidence}")
    print(f"Entities: {result.extracted_entities}")
    print("---")
```

---

## 🎨 UI Features

The Angular UI includes:

✅ **Real-time Chat Interface** - Natural conversation flow
✅ **Intent Visualization** - See detected intent and confidence
✅ **Quick Examples** - Pre-built example prompts
✅ **Session Management** - Conversation continuity
✅ **Markdown Support** - Rich text formatting in responses
✅ **Loading States** - Visual feedback during processing
✅ **Error Handling** - User-friendly error messages
✅ **Responsive Design** - Works on desktop and mobile
✅ **Conversation History** - Browse past messages

---

## 📊 System Architecture

```
User Input
    ↓
[Angular UI] → POST /api/v1/public/chat
    ↓
[Intent Classifier (LLM)]
    ↓
[Orchestrator Router]
    ↓
    ├─→ [Symptom Analysis Agent] → Gemini AI → Doctor Matching
    ├─→ [Insurance Verifier] → CSV Lookup → Provider Detection
    ├─→ [Appointment Scheduler] → SQLite DB → Email Notifications
    ├─→ [Hospital Guidance] → Navigation Tools → Queue Management
    └─→ [General Q&A] → Gemini AI → Health Information
    ↓
[Unified Response]
    ↓
[Angular UI Display]
```

---

## 🔍 Monitoring and Debugging

### Backend Logs

All requests are logged with:
- Intent classification results
- Agent routing decisions
- LLM responses
- Errors and warnings

View logs in console or check `logs/app.log`

### Frontend Console

Open browser DevTools to see:
- API requests/responses
- Service method calls
- Component state changes

---

## 🚧 Troubleshooting

### Backend Issues

**Issue:** `ModuleNotFoundError`
```bash
# Solution: Reinstall dependencies
pip install -r requirements-dev.txt
```

**Issue:** `GOOGLE_API_KEY not found`
```bash
# Solution: Set environment variable
export GOOGLE_API_KEY="your_key_here"  # Linux/Mac
set GOOGLE_API_KEY=your_key_here        # Windows
```

**Issue:** Database errors
```bash
# Solution: Delete and recreate database
rm app/data/appointments.db
# Restart server (will auto-create)
```

### Frontend Issues

**Issue:** `Cannot find module '@angular/core'`
```bash
# Solution: Reinstall node_modules
rm -rf node_modules package-lock.json
npm install
```

**Issue:** CORS errors
```bash
# Solution: Check backend CORS settings in app/core/config.py
# Ensure your frontend URL is in ALLOWED_ORIGINS
```

**Issue:** API connection refused
```bash
# Solution: Make sure backend is running on port 8000
# Check environment.ts has correct API URL
```

---

## 🎯 Next Steps

1. **Customize Insurance Providers**
   - Add CSV files in `app/data/insurance/`
   - Follow format: `blue_cross_blue_shield.csv`

2. **Add More Example Prompts**
   - Edit `chat.component.ts` → `examplePrompts` array

3. **Enhance Intent Classification**
   - Modify `app/services/intent_classifier.py`
   - Add more intent types or refine prompts

4. **Customize UI Theme**
   - Edit `chat.component.css`
   - Update color scheme and styling

5. **Deploy to Production**
   - Backend: Deploy to AWS/GCP/Azure
   - Frontend: Build and deploy to Netlify/Vercel
   - Update CORS and API URLs

---

## 📚 Additional Resources

- FastAPI Documentation: https://fastapi.tiangolo.com
- Angular Documentation: https://angular.io/docs
- LangGraph Documentation: https://langchain-ai.github.io/langgraph
- Google Gemini API: https://ai.google.dev

---

## 🤝 Support

For issues or questions:
1. Check the API documentation: `http://localhost:8000/docs`
2. Review logs: `logs/app.log`
3. Test with cURL before using UI
4. Verify environment variables are set correctly

---

**🎉 You're all set! Start chatting with your Healthcare AI Companion!**
