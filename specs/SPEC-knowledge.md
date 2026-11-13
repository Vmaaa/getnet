# Spec: knowledge

## Objective
Knowledge agent: answer Getnet product/service and general questions grounded in RAG passages, with DuckDuckGo web search for general-purpose questions. Returns `AgentResult` with exact-passage citations, or `needs_help` + gap. Prompts and answers in English.

## Tech Stack
- `app.rag.retriever`, `get_chat_model()` (LangChain), `ddgs` (DuckDuckGo search, no API key). Depends on `platform`, `rag`.

## Commands
```
Tests:  uv run pytest tests/knowledge -q
Manual: uv run python -m app.agents.knowledge_demo "How does receivables advance work?"
```

## Project Structure
```
src/app/agents/
  __init__.py
  knowledge.py      # KnowledgeAgent
  prompts/knowledge.py  # system prompt templates (English)
tests/knowledge/
```

## Code Style
```python
class KnowledgeAgent:
    def run(self, message: str, user_id: str | None = None) -> AgentResult: ...
```
Flow (single LLM call per pass):
1. `retrieve(message, k=rag_top_k)`.
2. Build context: refs `1..k`, one per passage, verbatim text.
3. If top score < `rag_min_score` (setting, default 0.3) or intent is general-purpose (weather, exchange rate, news), call DDG (`DDGS().text(message, region="us-en", max_results=5)`) and append results as further refs with `text` = result snippet, `url`, `title`.
4. Chat model via a LangChain `ChatPromptTemplate` (English); decision parsed with `.with_structured_output(KnowledgeDecision)` (fields: `answer`, `status`, `gap`), manual JSON parse only as fallback for endpoints without structured-output support. System prompt, in English:
   - Answer using ONLY the numbered context passages.
   - Cite every claim with its `[ref]` number.
   - If the context does not contain the answer, return `{"status": "needs_help", "gap": "<one sentence: what information is missing>"}` and never invent facts.
   - Respond in English regardless of the language of the passages.
5. Output `AgentResult`: `status=answered` → `answer` + `citations` = exactly the passages placed in the model context (refs `1..k` mirror what the model saw; `text` = exact passage). `status=needs_help` → `gap` filled, `citations=[]`.
6. Citations whose refs are never referenced in `answer` are still included (they were in the model's context); refs stay contiguous `1..k`.

## Testing Strategy
pytest with fake retriever + fake LLM: citation mapping (refs contiguous, text verbatim), needs_help path (gap sentence present, no citations), web-search fallback triggered on low score (fake DDG), English answer enforcement via prompt (asserted in prompt text).

## Boundaries
- Always: `citations` built from the actual context list, never from LLM output text.
- Ask first: changing the gap phrasing contract; adding another search provider.
- Never: let the LLM rewrite passage text inside `citations`; answer without context when retrieval scored below threshold and web search failed → return `needs_help`.

## Success Criteria
- "What's the difference between the Get Clássica and the Get Smart?" → answered, ≥2 citations with distinct URLs.
- "What's the weather forecast in Porto Alegre tomorrow?" → answered via web search, citations carry the source URLs.
- Unanswerable nonsense ("What is the airspeed velocity of a Getnet swallow?") → `needs_help` with a gap.

## Open Questions
None.
