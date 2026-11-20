from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.graph.workflow import healthcare_graph
from app.services.session import (
    get_conversation,
    add_message,
    clear_conversation,
)

# Create FastAPI app
app = FastAPI(
    title="RuralCare AI",
    version="0.6.0",
    description="Healthcare Triage Assistant"
)

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ─────────────────────────────────────────────
# Request/Response models
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    next_action: str
    message: str


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/")
async def home():
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "RuralCare AI"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main triage chat endpoint.
    Accepts a session_id and user message,
    runs the LangGraph workflow, and returns
    a triage response.
    """
    session_id = request.session_id
    user_message = request.message

    # Load conversation history
    conversation_history = get_conversation(session_id)

    # Build the LangGraph input state
    state = {
        "user_message": user_message,
        "conversation_history": conversation_history,
        "patient_information": {},
    }

    # Run the agentic workflow
    result = healthcare_graph.invoke(state)

    # Determine final urgency and message
    next_action = result.get("next_action", "NEED_MORE_INFORMATION")

    # Pick the appropriate response text based on urgency
    if next_action == "EMERGENCY":
        response_message = result.get(
            "emergency_response",
            "⚠️ This appears to be an emergency. Please call emergency services immediately or go to your nearest hospital.",
        )
    elif next_action == "URGENT":
        response_message = result.get(
            "urgent_response",
            "Your symptoms suggest you should seek medical attention soon. Please visit a clinic or hospital today.",
        )
    elif next_action == "ROUTINE":
        response_message = result.get(
            "routine_response",
            "Your symptoms appear to be routine. Consider scheduling an appointment with a healthcare provider.",
        )
    else:
        # NEED_MORE_INFORMATION — use planner response
        response_message = result.get(
            "planner_response",
            "Could you please tell me more about your symptoms?",
        )

    # Save messages to session
    add_message(session_id, "user", user_message)
    add_message(session_id, "assistant", response_message)

    return ChatResponse(
        next_action=next_action,
        message=response_message,
    )


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a conversation session."""
    clear_conversation(session_id)
    return {"status": "cleared", "session_id": session_id}