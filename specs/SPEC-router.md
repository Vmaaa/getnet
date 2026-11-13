# Spec: router

## Objective
Router agent: primary entry point. Classifies the message, decides which specialized agent handles it, and re-plans on `needs_help` using the gap — never with a repeated gap. Prompts and outputs in English.

## Tech Stack
- `app.llm`. Depends on `platform`, `knowledge`, `support`.

## Commands
```
Tests:  uv run pytest tests/router -q
```

## Project Structure
```
src/app/agents/
  router.py         # RouterAgent: route(), replan(gap)
  prompts/router.py
tests/router/
```

## Code Style
```python
class RouterAgent:
    def __init__(self, knowledge: KnowledgeAgent, support: SupportAgent): ...
    def route(self, message: str, user_id: str | None) -> AgentResult: ...
    def replan(self, gap: str, message: str, user_id: str | None) -> AgentResult: ...
```
- Classification (chat model, one call): `IntentDecision` via `.with_structured_output` → `{"intent": "knowledge" | "support", "reasoning": "..."}`. Knowledge intent = product/service/general-world questions; support intent = anything about this specific user's data (money, profile, device). Fallback heuristic on model failure: keyword rules (my/money/deposit/machine/device/user-specific → support; else knowledge). Heuristic decision logged.
- `route()` dispatches to the chosen agent and returns its `AgentResult` unchanged (router never rewrites agent output).
- Gap ledger: per-`RouterAgent`-instance `set` of normalized gaps (`gap.strip().lower()`). `replan(gap, ...)`: if normalized gap already in ledger → raise `GapExhausted` (graph turns this into triage); else add to ledger, re-classify with the gap injected ("previous attempt failed: {gap}"), dispatch, return result.
- Both agents are constructed once and reused (LLM client is shared; embedder is cached).

## Testing Strategy
pytest with fake knowledge/support agents: intent classification fallback rules, dispatch returns agent result untouched, `replan` adds gap to ledger, repeated gap raises `GapExhausted`, gap reclassification prompt includes the gap.

## Boundaries
- Always: ledger check before re-dispatch; log every routing decision (intent, reasoning, gap).
- Ask first: adding a third agent to the taxonomy (e.g., escalation).
- Never: re-dispatch on a gap already in the ledger; mutate `AgentResult` fields in transit.

## Success Criteria
- Scenario-level: deposit question → support; machine-difference question → knowledge; weather → knowledge (web search).
- Unit: identical gap twice → `GapExhausted` on the second `replan` call.

## Open Questions
None.
