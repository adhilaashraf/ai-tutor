# 🤖 AI Tutor — AI Learning System

A Flask-based AI tutoring system that explains topics, asks questions, evaluates answers, and gives feedback — powered by **Groq (LLaMA 3.1)**.

---

## 🚀 Setup & Run

### 1. Get a FREE Groq API Key
Go to → https://console.groq.com
- Sign up with Google (free, no credit card needed)
- Click "API Keys" → "Create API Key"
- Copy the key

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set your API key
Create a `.env` file in the project root:
```
GEMINI_API_KEY=your_groq_key_here
FLASK_SECRET_KEY=any_random_string
```

### 4. Run the app
```bash
python app.py
```
Open browser → http://localhost:5000

---

## 🧠 How It Works

```
User Input (Class + Subject + Topic + Difficulty)
        ↓
[Prompt 1] → Groq (LLaMA 3.1) → Age-appropriate Explanation
        ↓
[Prompt 2] → Groq (LLaMA 3.1) → 3 Questions (difficulty-adjusted)
        ↓
Student types answers
        ↓
[Prompt 3] → Groq (LLaMA 3.1) → Evaluation + Per-question feedback + Score
        ↓
Results displayed with grade, feedback, improvement tip
```

---

## 💡 Prompt Engineering Decisions

### Why 3 separate prompts instead of 1?
- **Separation of concerns**: Each prompt is focused, reducing hallucination
- **Modularity**: User can re-read explanation before quiz, retry independently
- **Cost efficiency**: Only call what's needed — no wasted tokens

### Temperature = 0.4
Low temperature ensures consistent, factual educational content. High temperature would cause creative but inaccurate explanations.

### Age-appropriate mapping
Explicit age context in prompt (e.g., "10-11 year old") ensures the model calibrates vocabulary accurately without guessing from class grade alone.

### Anti-hallucination measure
Questions are generated *from the explanation text* (injected into prompt), not from general knowledge. This ensures students can actually answer questions from what they studied.

---

## 🔥 Final Question: 10,000 Students Daily

### What will break first?

**1. API Rate Limits (breaks first)**
- Groq free tier: 30 requests/minute, 14,400/day
- 10,000 students × 3 API calls = 30,000 calls/day → FREE TIER FAILS
- Fix: Upgrade to Groq paid tier + Redis caching for popular topics (60-70% cache hit rate)

**2. Flask Dev Server (breaks immediately)**
- `app.run(debug=True)` is single-threaded
- Fix: Deploy with Gunicorn: `gunicorn -w 4 -b 0.0.0.0:8000 app:app` + Nginx reverse proxy

**3. Session Storage (breaks under scale)**
- Flask cookie sessions fail at scale
- Fix: Redis-backed sessions via `flask-session`

**4. Prompt Injection Risk**
- Students could type malicious topics
- Fix: Input sanitization + system-level prompt guards

### Production Architecture for 10K Students:
```
Students → Nginx → Gunicorn (4+ workers) → Flask App
                                              ↓
                                         Redis Cache + Sessions
                                              ↓
                                         Groq API (paid tier)
```

**Estimated cost**: ~$60/month for 10,000 daily active users (with caching) ✅

---

## 📁 Project Structure
```
ai-tutor/
├── app.py                  # Flask backend + prompt engineering
├── templates/
│   └── index.html          # Web UI (4-step flow)
├── requirements.txt        # Dependencies
├── sample_output.json      # Sample I/O for submission
├── .gitignore              # Keeps API key safe
└── README.md
```

---

## 🛠️ Tech Stack
- **Backend**: Python, Flask
- **AI Model**: LLaMA 3.1 8B Instant via Groq API (free tier)
- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Environment**: python-dotenv
