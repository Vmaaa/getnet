import logging
from typing import Literal

from pydantic import BaseModel

from app.agents.knowledge import KnowledgeAgent
from app.agents.prompts.router import CLASSIFIER_SYSTEM
from app.agents.support import SupportAgent
from app.contracts import AgentResult
from app.llm import get_chat_model, structured_output

logger = logging.getLogger(__name__)

SUPPORT_HINTS = (
    "my ",
    "deposit",
    "money",
    "transaction",
    "sale",
    "settlement",
    "device",
    "machine won't",
    "machine is not",
    "profile",
    "minha",
    "recebimento",
    "depósito",
)


class IntentDecision(BaseModel):
    intent: Literal["knowledge", "support"]
    reasoning: str = ""


class GapExhausted(Exception):
    pass


def normalize_gap(gap: str) -> str:
    return " ".join(gap.lower().split())


def heuristic_intent(message: str) -> Literal["knowledge", "support"]:
    lowered = message.lower()
    return "support" if any(hint in lowered for hint in SUPPORT_HINTS) else "knowledge"


class RouterAgent:
    def __init__(self, knowledge: KnowledgeAgent, support: SupportAgent, chat_model=None):
        self.knowledge = knowledge
        self.support = support
        self._chat_model = chat_model
        self._ledger: set[str] = set()

    def reset_gaps(self) -> None:
        self._ledger.clear()

    def has_gap(self, gap: str) -> bool:
        return normalize_gap(gap) in self._ledger

    def register_gap(self, gap: str) -> None:
        self._ledger.add(normalize_gap(gap))

    def _model(self):
        return self._chat_model if self._chat_model is not None else get_chat_model()

    def classify(self, message: str, gap: str | None = None) -> tuple[Literal["knowledge", "support"], str]:
        user_content = message if not gap else f"{message}\n\nPrevious attempt failed with this gap: {gap}. Take the gap into account."
        try:
            decision = structured_output(
                self._model(),
                IntentDecision,
                [
                    {"role": "system", "content": CLASSIFIER_SYSTEM},
                    {"role": "user", "content": user_content},
                ],
            )
            if decision is not None and decision.intent in ("knowledge", "support"):
                return decision.intent, decision.reasoning
        except Exception as exc:
            logger.warning("classification failed error=%s", exc)
        intent = heuristic_intent(message)
        return intent, "heuristic fallback"

    def _dispatch(self, intent, message, user_id) -> AgentResult:
        agent = self.support if intent == "support" else self.knowledge
        return agent.run(message, user_id)

    def route(self, message: str, user_id: str | None = None) -> AgentResult:
        intent, reasoning = self.classify(message)
        logger.info("route intent=%s reasoning=%s", intent, reasoning)
        return self._dispatch(intent, message, user_id)

    def replan(self, gap: str, message: str, user_id: str | None = None) -> AgentResult:
        if self.has_gap(gap):
            raise GapExhausted(gap)
        self.register_gap(gap)
        intent, reasoning = self.classify(message, gap=gap)
        logger.info("replan intent=%s gap=%r reasoning=%s", intent, gap, reasoning)
        return self._dispatch(intent, message, user_id)
