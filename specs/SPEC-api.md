# Spec: api

## Objective
FastAPI HTTP surface: `POST /chat` accepting the grader payload, returning the graph's final envelope; `/health` for container healthcheck. This is the contract with the evaluator.

## Tech Stack
- `fastapi`, `uvicorn`. Depends on `graph`.

## Commands
```
Dev:     uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
Tests:   uv run pytest tests/api -q
Curl:    curl -s localhost:8000/chat -H 'content-type: application/json' \
           -d '{"message": "What is the Get Smart?", "user_id": "cliente1988"}' | jq
```

## Project Structure
```
src/app/api/
  main.py       # FastAPI app, lifespan warm-up, routes
  schemas.py    # ChatRequest, ChatResponse (mirrors FinalResponse)
tests/api/
```

## Code Style
```python
class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    user_id: str | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    get_embedder()
    get_collection()
    yield

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse: ...
```
- `POST /chat` → validate → compiled LangGraph app via `Orchestrator.handle(message, user_id)` → `ChatResponse{status, answer, citations, tools_used, agent_trace, session_id}`. 422 on invalid payload (FastAPI default, pydantic).
- `GET /health` → `{"status": "ok", "chroma_chunks": <int>, "embedder": "loaded"}`; used by compose healthcheck.
- Lifespan warm-up: load embedder + open Chroma **before** the server accepts requests (first-request latency, constitution §5).
- `user_id` optional: support intent without it degrades to `needs_help` → triage per support spec.

## Testing Strategy
pytest with `TestClient` and the orchestrator injected/faked: 200 + schema keys for knowledge and support intents, triage envelope passthrough, 422 on empty message / wrong types, health returns chunk count.

## Boundaries
- Always: one orchestrator instance per app process; response mirrors `FinalResponse` exactly.
- Ask first: adding auth, CORS, rate limiting (out of MVP scope).
- Never: business logic in the API layer; swallow orchestrator exceptions into a 200 — unexpected errors return 500 with a JSON body.

## Success Criteria
- All 10 example scenarios return 200 with the documented schema.
- `GET /health` 200 immediately after container start (post-warm-up).

## Open Questions
None.
