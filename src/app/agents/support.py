import json
import logging
from typing import Literal, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents.mock_bank import get_user_profile
from app.agents.prompts.support import SYSTEM_PROMPT
from app.agents.tools import SUPPORT_TOOLS
from app.contracts import AgentResult
from app.llm import get_chat_model

logger = logging.getLogger(__name__)

MAX_TOOL_STEPS = 4


class LoopState(TypedDict):
    messages: list[AnyMessage]
    steps: int


def build_tool_loop(model):
    def model_node(state: LoopState) -> dict:
        ai = model.invoke(state["messages"])
        return {"messages": [*state["messages"], ai], "steps": state["steps"] + 1}

    def tool_node(state: LoopState) -> dict:
        ai = state["messages"][-1]
        outputs = []
        for call in ai.tool_calls:
            tool = next(t for t in SUPPORT_TOOLS if t.name == call["name"])
            result = tool.invoke(call["args"])
            outputs.append(
                ToolMessage(
                    content=json.dumps(result, default=str, ensure_ascii=False),
                    tool_call_id=call["id"],
                    name=call["name"],
                )
            )
        return {"messages": [*state["messages"], *outputs]}

    def route(state: LoopState) -> Literal["tools", "__end__"]:
        if state["steps"] >= MAX_TOOL_STEPS:
            return END
        ai = state["messages"][-1]
        return "tools" if ai.tool_calls else END

    graph = StateGraph(LoopState)
    graph.add_node("model", model_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")
    return graph.compile()


class SupportAgent:
    def __init__(self, chat_model=None):
        self._chat_model = chat_model
        self._loop = None

    def _model(self):
        return (self._chat_model if self._chat_model is not None else get_chat_model()).bind_tools(SUPPORT_TOOLS)

    def run(self, message: str, user_id: str | None = None) -> AgentResult:
        if not user_id:
            return AgentResult(
                agent="support",
                status="needs_help",
                gap="user identifier missing",
            )
        profile = get_user_profile(user_id)
        if profile is None:
            return AgentResult(
                agent="support",
                status="answered",
                answer=f"User {user_id} not found.",
                tools_used=["get_user_profile"],
            )
        if self._loop is None:
            self._loop = build_tool_loop(self._model())
        final_state = self._loop.invoke(
            {
                "messages": [
                    SystemMessage(content=SYSTEM_PROMPT.format(user_id=user_id)),
                    HumanMessage(content=message),
                ],
                "steps": 0,
            }
        )
        messages = final_state["messages"]
        tools_used = list(dict.fromkeys(m.name for m in messages if isinstance(m, ToolMessage)))
        last = messages[-1]
        if last.tool_calls:
            return AgentResult(
                agent="support",
                status="needs_help",
                gap="could not gather enough customer data within the tool step limit",
                tools_used=tools_used,
            )
        logger.info("support answered tools=%s", tools_used)
        return AgentResult(
            agent="support",
            status="answered",
            answer=last.text(),
            tools_used=tools_used,
        )
