# Spec: graph

## Objective
Orchestration supervisor as a LangGraph `StateGraph`: routes messages between agents (control transfer via graph edges), enforces max 2 passes in edge code, falls back to triage on exhaustion, assembles the final response envelope. English only.

## Tech Stack
- `langgraph` (`StateGraph`, conditional edges). Depends on `router` only (router owns knowledge/support).

## Commands
```
Tests:  uv run pytest tests/graph -q
```

## Project Structure
```
src/app/graph/
  state.py          # GraphState TypedDict
  builder.py        # StateGraph assembly + compile()
  orchestrator.py   # Orchestrator.handle(message, user_id) -> FinalResponse
tests/graph/
```

## Contracts (owned here, built from platform contracts)
```python
class TraceEntry(BaseModel):
    attempt: int
    agent: Literal["knowledge", "support"]
    status: Literal["answered", "needs_help"]
    gap: str | None = None

class FinalResponse(BaseModel):
    status: Literal["answered", "triage"]
    answer: str
    citations: list[Citation] = []
    tools_used: list[str] = []
    agent_trace: list[TraceEntry] = []
    session_id: str

class GraphState(TypedDict):
    message: str
    user_id: str | None
    attempt: int
    seen_gaps: set[str]
    trace: list[TraceEntry]
    result: AgentResult | None
```

## Code Style
```python
MAX_PASSES = 2

builder = StateGraph(GraphState)
builder.add_node("route", route_node)
builder.add_node("knowledge", knowledge_node)
builder.add_node("support", support_node)
builder.add_node("triage", triage_node)
builder.add_conditional_edges("route", pick_agent)
builder.add_conditional_edges("knowledge", after_agent)
builder.add_conditional_edges("support", after_agent)

def after_agent(state) -> str:
    if state["result"].status == "answered":
        return END
    if state["attempt"] >= MAX_PASSES:
        return "triage"
    if normalize(state["result"].gap) in state["seen_gaps"]:
        return "triage"
    return "route"
```
- Nodes: `route` calls the router (first pass: classify; replan passes: re-classify with gap injected, ledger checked here, `GapExhausted` → triage); `knowledge`/`support` invoke their agent and store `AgentResult` in state; `triage` writes the fixed English fallback answer. A tiny `finalize` step (or post-invocation assembly) builds `FinalResponse`.
- Pass cap: `MAX_PASSES = 2` enforced by `attempt` counter + conditional edge in graph code, never by prompt.
- Exhaustion paths (no answer after pass 2, or repeated gap) → triage `FinalResponse`: `status="triage"`, fixed English message explaining the system could not resolve the request and suggesting human support channels, empty citations, accumulated `tools_used`, full trace.
- Success path: passes through the last `AgentResult` (`answer`, `citations`, `tools_used`) with `status="answered"`.
- `session_id`: `uuid4().hex` per `handle()` call. Graph compiled once per process; no checkpointer (stateless sessions).

## Testing Strategy
pytest with fake router/agents injected into the builder: answered-first-pass → single trace entry, pass-2 success → two entries, pass-2 `needs_help` → triage, repeated gap → triage, citations/tools passthrough untouched, trace order.

## Boundaries
- Always: build the envelope from actual `AgentResult`s; log pass count + final status; keep the graph acyclic beyond the single `route` loop.
- Ask first: changing `MAX_PASSES`, `GraphState`, or `FinalResponse` schema (breaks API + grader contract); adding nodes (e.g., escalation agent).
- Never: implement retry logic inside agents (it belongs in the graph); drop trace entries on triage; use `recursion_limit` as a substitute for the explicit pass counter.

## Success Criteria
- Contract scenario "knowledge fails pass 1 with gap G, knowledge answers pass 2 after replan(G)" → `status=answered`, 2 trace entries.
- "knowledge fails pass 1 with G, replan returns G again" → triage on attempt 2.
- Every HTTP-visible response carries a complete `agent_trace`.

## Open Questions
None.
