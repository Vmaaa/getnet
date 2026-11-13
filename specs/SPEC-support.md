# Spec: support

## Objective
Support agent: resolve customer-specific questions (profile, money movement/settlement, device health) via a bounded tool loop over deterministic mock data. Unknown user → explicit "user not found" outcome. `tools_used` reflects actual execution. Prompts and answers in English. Built with LangChain tool-calling; loop bounded inside a small LangGraph subgraph.

## Tech Stack
- `app.llm` (LangChain chat model), `langchain` (`@tool`, `bind_tools`), `langgraph` (bounded loop subgraph). Depends on `platform` (not `rag`).

## Commands
```
Tests:  uv run pytest tests/support -q
Manual: uv run python -m app.agents.support_demo "When will yesterday's sales be deposited?" cliente1988
```

## Project Structure
```
src/app/agents/
  support.py        # SupportAgent: compiles the bounded tool-loop subgraph
  tools.py          # langchain @tool defs over the mock bank
  prompts/support.py
data/
  mock_bank.py      # deterministic dataset generator (dates relative to today)
tests/support/
```

## Code Style
```python
MAX_TOOL_STEPS = 4

@tool
def get_transactions(user_id: str) -> list[dict]: ...
```
- Tools (LangChain `@tool` over deterministic mock data; dates generated relative to `datetime.now(UTC)`; Getnet settlement rules D+1/D+2):
  - `get_user_profile(user_id)` → `{name, plan, machine_model, account_status}` or `None`.
  - `get_transactions(user_id)` → list of `{id, gross_amount_brl, net_amount_brl, sale_date, settlement_date, status}` (settlement dates included — required by contract).
  - `get_device_status(user_id)` → `{device_model, connectivity, last_sync_at, last_error}`.
- Loop: LangGraph subgraph with state `{messages, steps}`; model node calls `model.bind_tools(tools)`, tool node executes and appends `ToolMessage`s. Conditional edge ends the loop when the model returns no tool calls or when `steps >= MAX_TOOL_STEPS`. **The cap lives in the edge function, not the prompt.**
- `tools_used` = names of tools that actually executed, read from the `ToolMessage`s in the final state — fabrication impossible by construction.
- Unknown user: first `get_user_profile` returning `None` → immediately return `AgentResult(status="answered", answer="User {user_id} not found...", tools_used=[...executed...])`.
- Step exhaustion without a final message → `AgentResult(status="needs_help", gap=...)`.
- No user_id in request → `needs_help` with gap "user identifier missing".

## Testing Strategy
pytest with a fake chat model (scripted tool-call sequences injected via a FakeToolCallingModel): cap enforced at 4 steps, `tools_used` matches executed tools only, unknown-user path short-circuits, final answer path returns answer + empty citations, settlement dates present in tool output.

## Boundaries
- Always: execute tools through the LangChain tool node (single source of truth); derive `tools_used` from message history.
- Ask first: adding a fourth tool; changing mock-data schema.
- Never: let the model invent transaction data — answers must quote tool results; exceed 4 steps; count `tools_used` entries the model merely mentioned but never executed.

## Success Criteria
- "When will the money from yesterday's sales be deposited?" (cliente1988) → answered citing settlement_date from `get_transactions`, `tools_used` includes `get_transactions`.
- "My card machine won't connect to the internet" (cliente1988) → answered using `get_device_status`.
- `"ghost_user"` → "user not found" outcome.

## Open Questions
- Contract reads "unknown user → user not found" as a definitive outcome, so I map it to `status="answered"` with that message. If you prefer `needs_help` + gap, say so at the gate.
