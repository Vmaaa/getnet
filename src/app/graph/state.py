from typing import Literal, TypedDict

from pydantic import BaseModel, Field

from app.contracts import AgentResult, Citation


class TraceEntry(BaseModel):
    attempt: int
    agent: Literal["knowledge", "support"]
    status: Literal["answered", "needs_help"]
    gap: str | None = None


class FinalResponse(BaseModel):
    status: Literal["answered", "triage"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    agent_trace: list[TraceEntry] = Field(default_factory=list)
    session_id: str


class GraphState(TypedDict):
    message: str
    user_id: str | None
    attempt: int
    intent: str
    result: AgentResult | None
    trace: list[TraceEntry]
