import logging
import uuid
from typing import Literal

from langgraph.graph import END, START, StateGraph

from app.agents.knowledge import KnowledgeAgent
from app.agents.router import RouterAgent
from app.agents.support import SupportAgent
from app.contracts import AgentResult
from app.graph.state import FinalResponse, GraphState, TraceEntry

logger = logging.getLogger(__name__)

MAX_PASSES = 2


def build_orchestrator() -> Orchestrator:
    knowledge = KnowledgeAgent()
    support = SupportAgent()
    return Orchestrator(RouterAgent(knowledge, support))

TRIAGE_ANSWER = (
    "I could not resolve this request with the information available. "
    "Our team will follow up on it. In the meantime, please reach Getnet's human support "
    "through the Getnet app or at www.getnet.net."
)


def _entry(attempt: int, result: AgentResult) -> TraceEntry:
    return TraceEntry(attempt=attempt, agent=result.agent, status=result.status, gap=result.gap)


def build_app(router: RouterAgent):
    def route_node(state: GraphState) -> dict:
        reentry = state["result"] is not None
        attempt = state["attempt"] + 1 if reentry else state["attempt"]
        gap = state["result"].gap if reentry else None
        intent, reasoning = router.classify(state["message"], gap=gap)
        logger.info("graph route attempt=%d intent=%s gap=%r", attempt, intent, gap)
        return {"attempt": attempt, "intent": intent}

    def knowledge_node(state: GraphState) -> dict:
        result = router.knowledge.run(state["message"], state["user_id"])
        return {"result": result, "trace": [*state["trace"], _entry(state["attempt"], result)]}

    def support_node(state: GraphState) -> dict:
        result = router.support.run(state["message"], state["user_id"])
        return {"result": result, "trace": [*state["trace"], _entry(state["attempt"], result)]}

    def pick_agent(state: GraphState) -> Literal["knowledge", "support"]:
        return "support" if state["intent"] == "support" else "knowledge"

    def after_agent(state: GraphState) -> Literal["route", "triage", "__end__"]:
        result = state["result"]
        if result.status == "answered":
            return END
        if state["attempt"] >= MAX_PASSES:
            return "triage"
        gap = result.gap or ""
        if not gap or router.has_gap(gap):
            return "triage"
        router.register_gap(gap)
        return "route"

    def triage_node(state: GraphState) -> dict:
        logger.info("graph triage attempts=%d gap=%r", state["attempt"], state["result"].gap)
        return {"result": state["result"]}

    graph = StateGraph(GraphState)
    graph.add_node("route", route_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("support", support_node)
    graph.add_node("triage", triage_node)
    graph.add_edge(START, "route")
    graph.add_conditional_edges("route", pick_agent, {"knowledge": "knowledge", "support": "support"})
    graph.add_conditional_edges("knowledge", after_agent, {"route": "route", "triage": "triage", END: END})
    graph.add_conditional_edges("support", after_agent, {"route": "route", "triage": "triage", END: END})
    graph.add_edge("triage", END)
    return graph.compile()


class Orchestrator:
    def __init__(self, router: RouterAgent):
        self._router = router
        self._app = build_app(router)

    def handle(self, message: str, user_id: str | None = None) -> FinalResponse:
        self._router.reset_gaps()
        state = self._app.invoke(
            {
                "message": message,
                "user_id": user_id,
                "attempt": 1,
                "intent": "",
                "result": None,
                "trace": [],
            }
        )
        result: AgentResult = state["result"]
        trace = state["trace"]
        if result.status == "answered":
            return FinalResponse(
                status="answered",
                answer=result.answer,
                citations=result.citations,
                tools_used=result.tools_used,
                agent_trace=trace,
                session_id=uuid.uuid4().hex,
            )
        return FinalResponse(
            status="triage",
            answer=TRIAGE_ANSWER,
            tools_used=result.tools_used,
            agent_trace=trace,
            session_id=uuid.uuid4().hex,
        )
