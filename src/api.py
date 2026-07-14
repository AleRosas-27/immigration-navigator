"""
ImmigrationNavigator — FastAPI Backend
=======================================
UC Berkeley MIDS Capstone 2026

REST API that powers the ImmigrationNavigator web app.
Duc's frontend calls these endpoints.

Run locally:
    pip install fastapi uvicorn
    uvicorn src.api:app --reload --port 8000

Deploy on AWS Lambda:
    pip install mangum
    handler = Mangum(app)

Endpoints:
    POST /ask          — Main RAG question answering
    POST /deadlines    — Deadline calculator only
    GET  /health       — Health check
"""

import os
from datetime import date, datetime
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.rag import ask, initialize
from src.deadlines import calculate_deadlines, format_deadlines, deadlines_to_dict


# ── Lifespan — initialize pipeline once at startup ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the RAG pipeline when the server starts."""
    print("Initializing ImmigrationNavigator pipeline...")
    initialize()
    print("Pipeline ready.")
    yield
    # Cleanup on shutdown (nothing needed currently)


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="ImmigrationNavigator API",
    description=(
        "AI-powered guidance for the F-1 → OPT → STEM OPT → H-1B visa pipeline. "
        "Every answer is grounded in official USCIS sources with citations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the frontend to call this API
# Update origins to match the frontend URL in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # TODO: replace with frontend URL before production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class UserProfile(BaseModel):
    """The user's current immigration situation."""
    visa_status:     str = Field(default="F-1 student",
                                  example="F-1, currently on OPT")
    degree_field:    str = Field(default="Not specified",
                                  example="Computer Science (STEM)")
    graduation_date: str = Field(default="",
                                  example="2025-05-15",
                                  description="YYYY-MM-DD format")
    employer_type:   str = Field(default="Not specified",
                                  example="Full-time employer")


class AskRequest(BaseModel):
    """Request body for the /ask endpoint."""
    question: str = Field(
        example="When do I need to apply for OPT?",
        description="Natural language immigration question"
    )
    profile: UserProfile = Field(default_factory=UserProfile)
    include_deadlines: bool = Field(
        default=True,
        description="If True and graduation_date is set, append deadline timeline to answer"
    )


class AskResponse(BaseModel):
    """Response from the /ask endpoint."""
    answer:    str
    deadlines: Optional[dict] = None
    model:     str


class DeadlineRequest(BaseModel):
    """Request body for the /deadlines endpoint."""
    graduation_date: str = Field(
        example="2025-05-15",
        description="YYYY-MM-DD format"
    )


class DeadlineResponse(BaseModel):
    """Response from the /deadlines endpoint."""
    formatted: str
    data:      dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Health check endpoint. Returns 200 if the API is running."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/ask", response_model=AskResponse)
def ask_endpoint(req: AskRequest):
    """
    Main RAG question-answering endpoint.

    Takes a natural language question and a user profile,
    returns a cited, personalized answer from the USCIS corpus.

    If `include_deadlines` is True and `graduation_date` is provided,
    appends a personalized deadline timeline to the answer.
    """
    profile = {
        "visa_status":     req.profile.visa_status,
        "degree_field":    req.profile.degree_field,
        "graduation_date": req.profile.graduation_date,
        "employer_type":   req.profile.employer_type,
    }

    # Get RAG answer
    try:
        answer = ask(req.question, profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline error: {str(e)}")

    # Append deadline calculator if requested and graduation date is set
    deadlines_data = None
    deadline_keywords = ["deadline", "when", "date", "apply", "timeline", "expire", "window"]

    if (req.include_deadlines
            and req.profile.graduation_date
            and any(kw in req.question.lower() for kw in deadline_keywords)):
        try:
            grad_date = datetime.strptime(req.profile.graduation_date, "%Y-%m-%d").date()
            deadlines = calculate_deadlines(grad_date)
            answer += "\n\n---\n" + format_deadlines(deadlines)
            deadlines_data = deadlines_to_dict(deadlines)
        except ValueError:
            pass  # Invalid date format — skip calculator silently

    model_name = "OpenAI GPT-4o-mini" if os.getenv("USE_OPENAI", "false").lower() == "true" else "Groq Llama 3.3 70B"

    return AskResponse(
        answer=answer,
        deadlines=deadlines_data,
        model=model_name
    )


@app.post("/deadlines", response_model=DeadlineResponse)
def deadlines_endpoint(req: DeadlineRequest):
    """
    Deadline calculator endpoint.

    Takes a graduation date and returns a full personalized
    OPT / STEM OPT / H-1B timeline — no LLM involved.
    """
    try:
        grad_date = datetime.strptime(req.graduation_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD (e.g. 2025-05-15)"
        )

    deadlines = calculate_deadlines(grad_date)

    return DeadlineResponse(
        formatted=format_deadlines(deadlines),
        data=deadlines_to_dict(deadlines)
    )
