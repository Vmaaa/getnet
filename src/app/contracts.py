from typing import Literal

from pydantic import BaseModel, Field


class Passage(BaseModel):
    text: str
    url: str
    title: str
    lang: str = "pt-BR"
    breadcrumbs: str = ""
    score: float = 0.0


class Citation(BaseModel):
    ref: int
    url: str
    title: str
    text: str


class AgentResult(BaseModel):
    agent: Literal["knowledge", "support"]
    status: Literal["answered", "needs_help"]
    answer: str = ""
    gap: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
