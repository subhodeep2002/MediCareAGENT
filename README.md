# 🩺 MediCareAgent: An Agentic Healthcare Triage Assistant

<div align="center">

### A stateful, safety-first healthcare triage assistant built with FastAPI and LangGraph

*FastAPI · LangGraph · Groq · Deterministic Safety Guardrails*

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![FastAPI](https://img.shields.io/badge/FastAPI-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-blue)
![Groq](https://img.shields.io/badge/LLM-Groq-orange)
![Status](https://img.shields.io/badge/Status-Active%20Development-0F766E)

</div>

---

## 🌍 Overview

**MediCareAgent** is an agentic triage assistant. A patient describes their symptoms in a chat, the system asks follow-up questions, and it classifies the case as **EMERGENCY**, **URGENT**, **ROUTINE**, or **NEED_MORE_INFORMATION**.

It combines:

- 🔄 A **LangGraph** workflow with specialized LLM agents
- ⚡ **Parallel execution** of independent agents to reduce latency
- 🔒 A **deterministic emergency guardrail** that does not depend on the LLM
- ✅ An **LLM safety-validation agent** that reviews the triage decision
- 📋 **Structured extraction** of patient facts from free text
- 💬 **Session-based conversation history** with a bounded context window
- 🎨 A lightweight **browser chat interface**

> ⚠️ **Medical Disclaimer:** MediCareAgent is a student/portfolio project. It does not diagnose conditions and must not replace a licensed healthcare professional. In an emergency, contact local emergency services.

---

## 🎯 Problem Statement

A plain LLM chatbot can understand symptom descriptions, but using it alone for safety-critical decisions is risky: responses can be inconsistent, emergency signs can be missed, and token costs grow with every message.

MediCareAgent addresses this by splitting the work across specialized agents, adding a rule-based guardrail that can force emergency routing, and keeping the context sent to the LLM small.

---

## 🧩 LangGraph Workflow

```text
                START
                  │
         ┌────────┴────────┐
         ▼                 ▼
     Planner           Extractor        ← run in parallel
         │                 │
         └────────┬────────┘
                  ▼
               Triage                   ← waits for both
                  │
                  ▼
        Deterministic Guardrail         ← rule-based red-flag check
                  │
                  ▼
           Safety Agent                 ← LLM review of triage decision
                  │
     ┌──────────┬─┴────────┬──────────┐
     ▼          ▼          ▼          ▼
 Emergency   Urgent     Routine    Follow-up
     │          │          │          │
     └──────────┴────┬─────┴──────────┘
                     ▼
                    END
```

Routing after the safety agent is done with `add_conditional_edges`. If the deterministic guardrail fires, the case is always routed to **Emergency**, regardless of what the LLM agents decided.

---

## 🧠 Agents

| Node | Type | Responsibility |
|---|---|---|
| **Planner** | LLM | Reads the conversation, identifies missing information, and writes the next follow-up question |
| **Extractor** | LLM | Converts the conversation into structured patient fields (age, sex, symptoms, duration, temperature, …) |
| **Triage** | LLM | Assigns an urgency level from the available information |
| **Guardrail** | Deterministic | Scans the current message for red-flag combinations (e.g. chest pain + difficulty breathing, not breathing, severe bleeding) |
| **Safety** | LLM | Reviews planner, triage, and guardrail results; must preserve EMERGENCY if the guardrail fired and must not downgrade warning signs |
| **Emergency / Urgent / Routine / Follow-up** | Handlers | Produce the response for each outcome |

### Why parallel?

The planner and extractor both read only the incoming message and conversation history, so neither needs the other's output. Both are connected directly to `START`, and LangGraph runs them concurrently in the same step. Triage has incoming edges from both, so it runs only after both finish.

```python
graph.add_edge(START, "planner")
graph.add_edge(START, "extractor")
graph.add_edge("planner", "triage")
graph.add_edge("extractor", "triage")
```

---

## 🔒 Deterministic Safety Guardrail

Critical cases are not left entirely to the model. The guardrail (`app/agents/guardrail.py`) runs keyword rules on the raw current message, so it works even when the LLM asks for more information.

```text
Patient:   "I have chest pain and difficulty breathing."
Triage:    NEED_MORE_INFORMATION
Guardrail: triggered → EMERGENCY
Router:    emergency handler
```

Because it is keyword-based, it only catches the phrasings it lists. Expanding the rules and testing them against varied wording is on the roadmap.

---

## 💬 Conversation Management & Token Control

Sessions are stored in memory (`app/services/session.py`), keyed by `session_id`.

To stay within Groq's tokens-per-minute limits, only the **most recent messages** of a session are sent to the agents instead of the full history. This keeps each request small no matter how long the conversation runs.

> **Current limitation:** the session store keeps raw messages only. Extracted patient information is not yet saved between turns, so facts mentioned before the context window can be lost. Persisting the extractor's output per session is planned.

---

## 🔌 API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Serve the chat interface |
| `GET` | `/health` | Health check |
| `POST` | `/chat` | Run one triage turn |
| `DELETE` | `/session/{session_id}` | Clear a session |

**Request**

```json
{ "session_id": "patient-001", "message": "I have had a fever since yesterday." }
```

**Response**

```json
{ "next_action": "NEED_MORE_INFORMATION", "message": "What is your temperature, and do you have any other symptoms?" }
```

Interactive docs: `http://127.0.0.1:8000/docs`

---

## 🗂️ Project Structure

```text
MediCareAgent/
├── app/
│   ├── agents/
│   │   ├── planner.py        # follow-up question generation
│   │   ├── extractor.py      # structured patient fact extraction
│   │   ├── triage.py         # urgency classification
│   │   ├── guardrail.py      # deterministic red-flag rules
│   │   ├── safety.py         # LLM safety validation
│   │   ├── emergency.py
│   │   ├── urgent.py
│   │   ├── routine.py
│   │   └── followup.py
│   ├── graph/
│   │   ├── state.py          # shared HealthcareState (TypedDict)
│   │   └── workflow.py       # LangGraph StateGraph
│   ├── services/
│   │   ├── llm.py            # Groq client
│   │   └── session.py        # in-memory sessions
│   ├── config.py
│   └── main.py               # FastAPI app and routes
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── tests/
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

- **Backend:** Python 3.10+, FastAPI, Uvicorn, Pydantic
- **Agents:** LangGraph, LangChain Groq, Groq API
- **Frontend:** HTML, CSS, vanilla JavaScript
- **Testing:** Pytest

---

## 🚀 Getting Started

```bash
git clone https://github.com/devdeepsarkar/MediCareAgent.git
cd MediCareAgent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
GROQ_API_KEY=your_api_key
GROQ_MODEL=your_groq_model_id
```

Use any chat model ID your Groq account has access to. The current list is at the Groq console or via `GET https://api.groq.com/openai/v1/models`. Smaller models respond noticeably faster, since the workflow makes several LLM calls per message.

> ⚠️ Never commit `.env` or API keys. If a key is ever exposed, revoke it in the Groq console and create a new one.

Run the app:

```bash
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`.

Run tests:

```bash
pytest
```

---

## ⏱️ Performance Notes

Each chat turn makes several LLM calls (planner, extractor, triage, safety), so latency depends mostly on the model. Two changes reduced it:

1. Running the planner and extractor in parallel.
2. Using a smaller, faster Groq model.

In local testing, response time dropped from roughly 17s to roughly 5s. This was a small informal measurement, and most of the gain came from the model change.

---

## 📈 Status

**Implemented**

- [x] FastAPI backend and chat endpoint
- [x] LangGraph workflow with conditional routing
- [x] Parallel planner + extractor execution
- [x] Structured patient information extraction
- [x] LLM triage and safety-validation agents
- [x] Deterministic emergency guardrail
- [x] In-memory sessions with bounded context
- [x] Browser chat interface

**Planned**

- [ ] Persist extracted patient information across turns
- [ ] Prompt-injection guard, output guard, and PII redaction (`app/security/`)
- [ ] Full test coverage for API, triage routing, and guardrails
- [ ] Evaluation set for emergency recall and triage accuracy
- [ ] Appointment scheduling
- [ ] Redis/PostgreSQL session storage
- [ ] Authentication, Docker, deployment, monitoring

---

## 📄 License

MIT License.
