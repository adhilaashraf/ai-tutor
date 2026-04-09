import os
import json
import re
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
load_dotenv()
from groq import Groq
client = Groq(api_key=os.environ.get("GEMINI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ai-tutor-secret-2024")



def get_difficulty_label(difficulty: int) -> str:
    return {1: "very simple", 2: "moderate", 3: "challenging"}[difficulty]

def build_explanation_prompt(class_level: str, subject: str, topic: str, difficulty: int) -> str:
    difficulty_label = get_difficulty_label(difficulty)
    age_map = {"5th": "10-11 years old", "8th": "13-14 years old", "10th": "15-16 years old"}
    age = age_map.get(class_level, "school-going")

    return f"""You are an expert, friendly tutor for a {class_level} grade student ({age}).

Your task: Explain the topic "{topic}" from {subject} in a {difficulty_label} way.

Rules:
- Use simple, clear language appropriate for a {age} child
- Use 1-2 real-life analogies or examples they can relate to
- Keep explanation between 80-120 words
- Do NOT use jargon without explaining it
- End with one key takeaway sentence starting with "Remember:"
- For difficulty level {difficulty}/3: {"use very basic words, short sentences" if difficulty == 1 else "use moderate vocabulary, add one formula or concept" if difficulty == 2 else "go deeper, include edge cases or extensions of the concept"}

Respond ONLY with the explanation text. No headings, no bullet points."""


def build_questions_prompt(class_level: str, subject: str, topic: str, explanation: str, difficulty: int) -> str:
    difficulty_label = get_difficulty_label(difficulty)
    q_types = {
        1: "simple recall and fill-in-the-blank questions",
        2: "a mix of conceptual and application questions",
        3: "application, analysis, and a tricky reasoning question"
    }

    return f"""You are a {class_level} grade {subject} teacher.

Based on this explanation of "{topic}":
---
{explanation}
---

Create exactly 3 {difficulty_label} questions of type: {q_types[difficulty]}.

Rules:
- Questions must be directly answerable from the explanation
- Number them 1, 2, 3
- Keep each question under 20 words
- For difficulty {difficulty}/3: {"make them straightforward and confidence-building" if difficulty == 1 else "mix easy and medium questions" if difficulty == 2 else "make at least one question require thinking beyond the explanation"}
- Do NOT provide answers or hints

Respond ONLY in this JSON format (no markdown, no extra text):
{{
  "questions": [
    "Question 1 here",
    "Question 2 here", 
    "Question 3 here"
  ]
}}"""


def build_evaluation_prompt(topic: str, subject: str, class_level: str, questions: list, answers: list, explanation: str) -> str:
    qa_pairs = "\n".join([
        f"Q{i+1}: {q}\nStudent's Answer: {a if a.strip() else '[No answer given]'}"
        for i, (q, a) in enumerate(zip(questions, answers))
    ])

    return f"""You are a kind, encouraging {class_level} grade {subject} teacher evaluating a student's answers on "{topic}".

Reference explanation the student studied:
---
{explanation}
---

Student's answers:
{qa_pairs}

Evaluate each answer and provide overall feedback.

Rules:
- Be encouraging and positive even for wrong answers
- Point out what was correct first, then what to improve
- For wrong answers, give a hint toward the correct answer — do NOT just say "wrong"
- Score each question: correct / partially correct / incorrect
- Overall score out of 3
- Keep feedback concise and age-appropriate for {class_level} grade

Respond ONLY in this exact JSON format (no markdown, no extra text):
{{
  "score": "X/3",
  "percentage": 80,
  "grade": "Good",
  "per_question": [
    {{
      "question_no": 1,
      "status": "correct",
      "comment": "Great job! ..."
    }},
    {{
      "question_no": 2,
      "status": "partially correct",
      "comment": "You got part of it right..."
    }},
    {{
      "question_no": 3,
      "status": "incorrect",
      "comment": "Not quite, but think about..."
    }}
  ],
  "overall_feedback": "Overall encouraging message here...",
  "improvement_tip": "One specific actionable tip here..."
}}"""


def safe_parse_json(text: str) -> dict | None:
    """Extract JSON even if model adds extra text around it."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def call_gemini(prompt: str) -> str:
    """Call Groq with llama model and return text."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Groq API error: {str(e)}")

@app.route("/")
def index():
    session.clear()
    return render_template("index.html")


@app.route("/explain", methods=["POST"])
def explain():
    data = request.json
    class_level = data.get("class_level", "8th")
    subject = data.get("subject", "Math")
    topic = data.get("topic", "")
    difficulty = int(data.get("difficulty", 2))

    if not topic.strip():
        return jsonify({"error": "Topic cannot be empty"}), 400

    try:
        prompt = build_explanation_prompt(class_level, subject, topic, difficulty)
        explanation = call_gemini(prompt)

        
        session["class_level"] = class_level
        session["subject"] = subject
        session["topic"] = topic
        session["difficulty"] = difficulty
        session["explanation"] = explanation

        return jsonify({"explanation": explanation})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/questions", methods=["POST"])
def questions():
    explanation = session.get("explanation")
    class_level = session.get("class_level")
    subject = session.get("subject")
    topic = session.get("topic")
    difficulty = session.get("difficulty", 2)

    if not explanation:
        return jsonify({"error": "Please generate an explanation first"}), 400

    try:
        prompt = build_questions_prompt(class_level, subject, topic, explanation, difficulty)
        raw = call_gemini(prompt)
        parsed = safe_parse_json(raw)

        if not parsed or "questions" not in parsed:
            # Fallback: split by newlines if JSON fails
            lines = [l.strip() for l in raw.split("\n") if l.strip() and l[0].isdigit()]
            parsed = {"questions": lines[:3]}

        session["questions"] = parsed["questions"]
        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/evaluate", methods=["POST"])
def evaluate():
    data = request.json
    answers = data.get("answers", [])

    questions = session.get("questions")
    explanation = session.get("explanation")
    topic = session.get("topic")
    subject = session.get("subject")
    class_level = session.get("class_level")

    if not questions or not explanation:
        return jsonify({"error": "Session expired. Please start over."}), 400

    if len(answers) != len(questions):
        return jsonify({"error": "Please answer all questions"}), 400

    try:
        prompt = build_evaluation_prompt(topic, subject, class_level, questions, answers, explanation)
        raw = call_gemini(prompt)
        parsed = safe_parse_json(raw)

        if not parsed:
            return jsonify({"error": "Could not parse evaluation. Please try again."}), 500

        
        history = session.get("history", [])
        history.append({
            "topic": topic,
            "score": parsed.get("score"),
            "difficulty": session.get("difficulty")
        })
        session["history"] = history

        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history", methods=["GET"])
def history():
    return jsonify({"history": session.get("history", [])})


if __name__ == "__main__":
    app.run(debug=True, port=5000)