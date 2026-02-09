# Healthcare Companion - Quick Start Guide

## ✅ What We Built

A complete **AI-powered healthcare orchestration system** with automatic intent detection and routing.

---

## 🎯 Key Features

### 1. **Intelligent Intent Classification**
- 🧠 **LLM-based** (Gemini AI) with rule-based fallback
- 🎯 **6 Intent Types:** Symptom Analysis, Insurance, Appointments, Navigation, Health Q&A, Emergency
- 📊 **Confidence Scoring:** Know how certain the AI is
- 🔍 **Entity Extraction:** Automatically pull out key information

### 2. **Unified API Endpoint**
- **Single Entry Point:** `POST /api/v1/public/chat`
- **Automatic Routing:** No manual tool selection needed
- **Session Management:** Conversation continuity
- **Context-Aware:** Uses chat history for better understanding

### 3. **Beautiful Angular UI**
- 💬 **Chat Interface:** Real-time conversation
- 🏷️ **Intent Badges:** Visualize detected intent
- 📝 **Example Prompts:** Quick start options
- 🎨 **Markdown Support:** Rich text formatting
- 📱 **Responsive Design:** Works on all devices

---

## 🚀 Quick Start (5 Minutes)

### Backend Setup

```bash
# 1. Set environment variable
export GOOGLE_API_KEY="your_gemini_api_key_here"

# 2. Install dependencies (if not already done)
pip install -r requirements-dev.txt

# 3. Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: `http://localhost:8000`
✅ API docs at: `http://localhost:8000/docs`

### Frontend Setup

```bash
# 1. Navigate to frontend
cd frontend/angular

# 2. Install dependencies
npm install

# 3. Start dev server
ng serve
```

✅ UI running at: `http://localhost:4200`

---

## 💬 How to Use

### Just Type Naturally!

**Example 1: Symptom Analysis**
```
User: "I have a fever and cough for 3 days"
AI:   ✅ Detected: symptom_analysis (95% confidence)
      → Routes to Symptom Agent
      → Returns analysis + doctors
```

**Example 2: Insurance**
```
User: "Verify my Blue Cross insurance ABC123"
AI:   ✅ Detected: insurance_verification (92% confidence)
      → Routes to Insurance Verifier
      → Returns verification result
```

**Example 3: Emergency**
```
User: "Severe chest pain, can't breathe"
AI:   🚨 Detected: emergency (98% confidence)
      → IMMEDIATE response: Call 911!
```

---

## 📁 What Was Created

### Backend Files
```
app/
├── services/intent_classifier.py      # 🧠 Intent classification
├── agents/orchestrator/agent.py       # 🎯 Main orchestrator
└── api/v1/routes/unified_chat.py      # 🌐 Unified endpoint
```

### Frontend Files
```
frontend/angular/src/app/
├── models/chat.models.ts              # 📐 TypeScript types
├── services/chat.service.ts           # 📡 HTTP service
└── components/chat/
    ├── chat.component.ts              # 🎨 Main component
    ├── chat.component.html            # 📄 Template
    └── chat.component.css             # 🎨 Styling
```

---

## 🧪 Test It!

### Option 1: Use the UI
1. Open `http://localhost:4200`
2. Type any health-related message
3. Watch the AI detect intent and respond

### Option 2: Use cURL
```bash
curl -X POST http://localhost:8000/api/v1/public/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I have a fever and cough"}'
```

### Option 3: Use Python
```python
import requests

response = requests.post(
    'http://localhost:8000/api/v1/public/chat',
    json={'message': 'I have a headache'}
)

print(response.json())
```

---

## 📊 Intent Detection Examples

| Input | Intent | Confidence |
|-------|--------|------------|
| "I have a fever" | symptom_analysis | 95% |
| "Check my insurance" | insurance_verification | 90% |
| "Book appointment" | appointment_booking | 92% |
| "Where's the cafeteria?" | hospital_navigation | 88% |
| "What is diabetes?" | general_health_question | 85% |
| "Chest pain, can't breathe" | emergency | 98% |

---

## 🔄 System Flow

```
User Input
    ↓
[Intent Classifier] ← Gemini AI
    ↓
[Orchestrator]
    ↓
    ├─ Emergency? → Alert
    ├─ Symptoms? → Symptom Agent
    ├─ Insurance? → Verifier
    ├─ Appointment? → Scheduler
    ├─ Navigation? → Guide
    └─ Question? → LLM Q&A
    ↓
[Unified Response]
    ↓
[Display in UI]
```

---

## 📚 Full Documentation

- **Setup Guide:** `SETUP_GUIDE.md` - Detailed setup instructions
- **Architecture:** `ARCHITECTURE.md` - Technical details
- **API Docs:** `http://localhost:8000/docs` - Interactive docs

---

## 🎉 Success Checklist

✅ Backend running on port 8000
✅ Frontend running on port 4200
✅ Can type message and get response
✅ Intent badge shows correct intent
✅ Different message types work
✅ Session ID appears in header

---

## 💡 Pro Tips

1. **Start Simple:** Type "I have a fever"
2. **Check Intent:** Verify the intent badge
3. **Use Examples:** Click example prompts
4. **Check Logs:** Backend shows processing details
5. **Emergency Test:** Try "chest pain" to see emergency handling

---

**🎊 You're all set! Start chatting!**

Type anything health-related at `http://localhost:4200` and let the AI figure out what you need!
