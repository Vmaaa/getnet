# Getnet Multi-Agent Support System

A multi-agent customer support orchestration for Getnet (Brazilian payment company), built with **LangGraph**, **LangChain**, **Chroma** and **FastAPI**. Agents cooperate to answer product questions (RAG over Getnet's website + DuckDuckGo web search) and customer-specific questions (tool loop over account data), with a supervisor feedback loop, grounded citations and a bounded tool budget.

## Quick start

```bash
cp .env.example .env          # fill in OPENAI_BASE_URL, OPENAI_API_KEY, CHAT_MODEL
make run                      # purge stale images, build, boot compose stack
make ingest                   # populate the vector store (inside the container)
make smoke                    # run the 10-scenario HTTP smoke against :8000
```

Local development (no container):

```bash
uv sync                       # exact pins in pyproject.toml + uv.lock (Python 3.14)
uv run pytest -q              # unit tests (no LLM / no embedding model needed)
uv run uvicorn app.api.main:app --host 0.0.0.0 --port 8000
uv run python -m app.rag.ingest --reset
uv run python scripts/smoke_http.py --base-url http://localhost:8000
```

Configuration (`.env`):

| Variable | Purpose |
|---|---|
| `OPENAI_BASE_URL` | Chat endpoint base URL (any OpenAI-compatible server) |
| `OPENAI_API_KEY` | API key for the endpoint |
| `CHAT_MODEL` | Model name (e.g. `gpt-4o-mini`, `glm-4.6`) |
| `LLM_PROVIDER` | LangChain provider (`openai` default; `anthropic`, `ollama`, ... also work) |
| `LOG_LEVEL` | Logging verbosity |

Switching provider/model is a `.env` change only — agents obtain the model exclusively through `app.llm.get_chat_model()` (`init_chat_model`).

## Orchestration architecture

```
POST /chat {message, user_id}
        │
        ▼
┌─────────────────────────── LangGraph StateGraph ───────────────────────────┐
│  START → route ──(pick_agent)──→ knowledge ──┐                              │
│             ▲                 └─(pick_agent)→ support ──┤                   │
│             │                                           ▼                  │
│             └────────── needs_help + new gap ──── after_agent ──→ END      │
│                                            exhausted / repeated gap │      │
│                                                     ▼                │    │
│                                                  triage ─────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
{status, answer, citations[], tools_used[], agent_trace[], session_id}
```

- **Router Agent** (`app/agents/router.py`): classifies each message into `knowledge` or `support` via structured output, with a keyword fallback. Keeps a per-session gap ledger: on `needs_help` it re-plans with the injected gap, and a repeated gap raises `GapExhausted` — the same gap never drives two re-plans.
- **Knowledge Agent** (`app/agents/knowledge.py`): retrieves passages from Chroma; if scores are weak or the question is general-purpose (weather, exchange rates...), falls back to DuckDuckGo. The model answers only from numbered context passages, citing `[ref]`s. Insufficient context → `needs_help` + one-sentence gap, never a hallucination.
- **Support Agent** (`app/agents/support.py`): bounded LangGraph tool loop (max **4 steps**, enforced in the loop's edge function) over three tools: `get_user_profile`, `get_transactions` (with settlement dates), `get_device_status` — backed by deterministic mock bank data with D+1/D+2 settlement rules relative to today. Unknown user → `User {id} not found.`; `tools_used` is derived from actual `ToolMessage`s.
- **Graph supervisor** (`app/graph/builder.py`): max **2 passes** enforced in the conditional edge; exhaustion or a repeated gap yields a triage response suggesting human support. Every attempt is recorded in `agent_trace`.
- All prompts and answers are in English, regardless of the Portuguese source data.

## RAG pipeline

1. **Ingestion** (`app/rag/ingest.py`): crawls 18 fixed Getnet URLs (14 pt-BR product/FAQ pages + 4 English solution pages) with a browser-like UA; raw HTML + markdown cached under `data/raw/`.
2. **Chunking** (`app/rag/chunking.py`): heading-aware split of HTML→markdown text — chunks ≤900 chars with ~135-char carry-over overlap, each carrying `breadcrumbs`, `title`, `lang` and `chunk_index` metadata.
3. **Storage** (`app/rag/store.py`): embedded Chroma (cosine space) with deterministic sha1 ids; lives in the `chroma-data` named volume.
4. **Embeddings** (`app/rag/embedder.py`): `codefuse-ai/F2LLM-v2-0.6B` on CPU via sentence-transformers v6 asymmetric `encode_document` / `encode_query`, normalized, cosine similarity.
5. **Retrieval → generation**: top-k passages (default 5) are numbered `[1..k]` and given verbatim to the model; the response's `citations` array mirrors exactly what the model saw — `text` is the unmodified retrieved passage.

The embedding model (~1.2 GB) downloads into the `hf-cache` volume on first boot and is warmed up in the API lifespan before the server accepts requests.

## API

`POST /chat`

```json
{"message": "What's the difference between the Get Clássica and the Get Smart?", "user_id": "cliente1988"}
```

Response:

```json
{
  "status": "answered",
  "answer": "The Get Clássica is... [1] ...",
  "citations": [{"ref": 1, "url": "...", "title": "...", "text": "exact retrieved passage"}],
  "tools_used": [],
  "agent_trace": [{"attempt": 1, "agent": "knowledge", "status": "answered", "gap": null}],
  "session_id": "..."
}
```

`GET /health` → `{"status": "ok", "chroma_chunks": N, "embedder": "loaded"}` (used by the compose healthcheck).

## Testing strategy

- **Unit** (pytest, 70+ tests): contracts, config, chunker (sizes/overlap/breadcrumbs), store round-trips and retriever ordering with fake embeddings, knowledge agent citation mirroring and `needs_help`, support loop bounds with scripted fake tool-calling models, router gap ledger, graph pass cap/triage/trace with fake router, API contract tests with a faked orchestrator. No test touches the network or the embedding model — expensive components sit behind injectable protocols.
- **Integration** (`scripts/smoke_http.py`): the 10 challenge scenarios against the real compose stack, asserting schema, contiguous citation refs, real tool names, trace integrity and non-empty English answers; exits non-zero on any failure.

## Container notes

- Image: `python:3.14-slim` + `uv 0.13.8`, dependencies installed with `uv sync --frozen --no-dev`; torch CPU via the `pytorch-cpu` uv index (no GPU layers).
- Data safety: Chroma and the HF model cache live in **named volumes** (`chroma-data`, `hf-cache`) — no bind mounts, so rootless podman uid mapping can't break writes.
- `make run` purges dangling images before `up` to avoid reusing stale images from earlier attempts.

## Spec-driven development

This project was built under a gated SDD flow. See `specs/constitution.md` (principles + behavior contracts), `specs/capability-map.md` (module map), `specs/SPEC-*.md` (per-module specs) and `tasks/plan.md` / `tasks/todo.md` (plan + task breakdown).
