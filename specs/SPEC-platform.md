# Spec: platform

## Objective
Shared foundation every other module imports: environment config, structured logging, the model-agnostic chat-model factory (LangChain), and the domain contracts (`AgentResult`, `Citation`, `Passage`). No business logic here.

## Tech Stack
- Python 3.14, uv 0.13.8, src layout.
- `pydantic` (contracts, settings), `langchain` + `langchain-openai` (model-agnostic chat model). Exact `==` pins locked in `tasks/plan.md` via `uv.lock`.

## Commands
```
Sync:   uv sync
Tests:  uv run pytest tests/platform -q
Check:  uv run python -c "from app.config import get_settings; print(get_settings().chat_model)"
```

## Project Structure
```
src/app/
  __init__.py
  config.py        # pydantic-settings, cached get_settings()
  logging.py       # stdlib logging, one-line structured format
  contracts.py     # Citation, AgentResult, Passage
  llm.py           # get_chat_model(): model-agnostic factory
tests/platform/    # unit tests
```

## Code Style
```python
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

def get_chat_model() -> BaseChatModel:
    return init_chat_model(
        settings.chat_model,
        model_provider=settings.llm_provider,
        base_url=settings.openai_base_url,
        api_key=settings.openai_api_key,
        temperature=0,
        timeout=60,
        max_retries=2,
    )
```
- Settings: `openai_base_url`, `openai_api_key`, `chat_model`, `llm_provider="openai"`, `rag_top_k=5`, `rag_min_score=0.3`, `chroma_dir`, `hf_cache`, `log_level`; loaded from `.env`. `llm_provider` defaults to `openai` (any OpenAI-compatible endpoint works through `base_url`); switching provider string swaps to anthropic/ollama/etc. — model-agnostic.
- `get_chat_model()` is cached (one instance per process). Structured outputs downstream use `.with_structured_output(PydanticModel)`; agents must tolerate providers without native JSON support via the structured-output fallback chain, never raw string parsing first.
- No comments, no docstrings.

## Testing Strategy
pytest unit tests only: contract validation (bad status rejected), settings defaults + `.env` override, `get_chat_model()` returns cached instance configured with the right provider/base_url (asserted on the object, no network).

## Boundaries
- Always: import contracts from `app.contracts`; get the chat model via `get_chat_model()`; get settings via `get_settings()`.
- Ask first: adding any dependency; changing contract field names (breaks every module + API); adding a provider to the factory.
- Never: log API keys; instantiate provider chat-model classes anywhere but `llm.py`.

## Success Criteria
- All other modules type-annotate against `AgentResult`/`Citation`/`Passage` from `app.contracts` and obtain LLMs only via `get_chat_model()`.
- `uv run pytest tests/platform -q` green.
- Swapping `llm_provider`/`chat_model` in `.env` requires zero code changes.

## Open Questions
None.
