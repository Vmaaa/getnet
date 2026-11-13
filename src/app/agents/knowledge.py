import logging
from typing import Literal

from pydantic import BaseModel

from app.agents.prompts.knowledge import SYSTEM_PROMPT, USER_TEMPLATE
from app.config import get_settings
from app.contracts import AgentResult, Citation, Passage
from app.llm import get_chat_model, structured_output
from app.rag.retriever import retrieve

logger = logging.getLogger(__name__)

GENERAL_KEYWORDS = (
    "weather",
    "forecast",
    "temperature",
    "exchange rate",
    "dollar",
    "euro",
    "cotação",
    "clima",
    "news",
    "stock",
)


class KnowledgeDecision(BaseModel):
    status: Literal["answered", "needs_help"]
    answer: str = ""
    gap: str | None = None


def is_general_purpose(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in GENERAL_KEYWORDS)


def needs_web_search(message: str, passages: list[Passage]) -> bool:
    if not passages:
        return True
    if is_general_purpose(message):
        return True
    return max(p.score for p in passages) < get_settings().rag_min_score


def web_results(message: str) -> list[Passage]:
    from ddgs import DDGS

    try:
        results = DDGS().text(message, region="us-en", max_results=5)
    except Exception as exc:
        logger.warning("web search failed error=%s", exc)
        return []
    return [
        Passage(text=r["body"], url=r["href"], title=r["title"], score=0.5)
        for r in results
        if r.get("body") and r.get("href")
    ]


def format_context(passages: list[Passage]) -> str:
    return "\n\n".join(f"[{i}] {p.text}" for i, p in enumerate(passages, start=1))


class KnowledgeAgent:
    def __init__(self, chat_model=None, retriever=retrieve, web_search=web_results):
        self._chat_model = chat_model
        self._retriever = retriever
        self._web_search = web_search

    def _model(self):
        return self._chat_model if self._chat_model is not None else get_chat_model()

    def run(self, message: str, user_id: str | None = None) -> AgentResult:
        passages = self._retriever(message)
        if needs_web_search(message, passages):
            passages = passages + self._web_search(message)
        if not passages:
            return AgentResult(
                agent="knowledge",
                status="needs_help",
                gap="no information could be retrieved for this question",
            )
        decision = structured_output(
            self._model(),
            KnowledgeDecision,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TEMPLATE.format(question=message, context=format_context(passages))},
            ],
        )
        if decision is None:
            return AgentResult(
                agent="knowledge",
                status="needs_help",
                gap="the language model could not produce a grounded decision",
            )
        if decision.status == "needs_help":
            return AgentResult(
                agent="knowledge",
                status="needs_help",
                gap=decision.gap or "the retrieved context does not contain the answer",
            )
        citations = [
            Citation(ref=i, url=p.url, title=p.title, text=p.text)
            for i, p in enumerate(passages, start=1)
        ]
        logger.info("knowledge answered citations=%d", len(citations))
        return AgentResult(
            agent="knowledge",
            status="answered",
            answer=decision.answer,
            citations=citations,
        )
