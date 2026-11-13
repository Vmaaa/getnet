# Implementation Plan: Getnet Multi-Agent Support System (MVP)

Implements specs in `specs/` (capability map: platform → rag → knowledge → support → router → graph → api → container-v2 → http-smoke), under the constraints in `specs/constitution.md`.

## Overview
Python 3.14 + uv 0.13.8 service: a LangGraph supervisor graph routing control between agents (max 2 passes, gap ledger, triage), LangChain model-agnostic agents, over a Chroma + F2LLM-v2-0.6B RAG stack, exposed via FastAPI and shipped as a compose stack with named volumes. Ingestion runs in the background and never blocks module implementation until `knowledge` needs the index.

## Architecture Decisions
- **LangGraph for control transfer**: `StateGraph` with route/knowledge/support/triage nodes; the 2-pass cap and gap-ledger check live in conditional-edge functions (constitution §4 "graph code" = graph edges, literally). The support tool loop is its own bounded subgraph with an explicit step counter — no reliance on `recursion_limit`.
- **Model-agnostic agents via LangChain**: `get_chat_model()` = `init_chat_model(chat_model, model_provider=llm_provider, base_url=...)`; agent decisions parsed with `.with_structured_output(PydanticModel)` plus a manual-JSON-parse fallback for endpoints without structured-output support. Switching provider/model = `.env` change only.
- **Fake-first boundaries**: every expensive component (LLM, embedder, Chroma) sits behind an injectable protocol, so all unit tests run without the 1.2 GB model or the real LLM endpoint.
- **Contracts stay framework-free**: `AgentResult`/`Citation`/`FinalResponse` are plain pydantic models independent of LangChain/LangGraph types; each agent adapts to them at its boundary, so the API and tests never import framework types.
- **Deterministic mock bank data** generated at import with dates relative to `today` (D+1/D+2 settlement) so settlement questions always make sense.
- **Ingest as background process**: started immediately after the rag slice lands; `support`/`router`/`graph`/`api` are built while it runs.
- **Root-container + named volumes**: avoids rootless-podman uid mapping issues from the postmortem; nothing bind-mounted.

## Vertical Slices (each leaves the system in a working, testable state)

### Slice 1 — Foundation (platform)
Package skeleton, contracts, settings, logging, model-agnostic chat-model factory (LangChain). Unit-testable without network.
Checkpoint: `uv run pytest tests/platform -q` green; deps pinned and locked.

### Slice 2 — RAG pipeline (rag)
Crawl → markdown → heading chunks → embeddings → Chroma; retriever with `EmbedFn` injection. Unit tests with fake embeddings; then **kick off real ingest in background**.
Checkpoint: chunker/store/retriever tests green; ingest running; `probe` answers "Get Clássica vs Get Smart" from the real index once done.

### Slice 3 — Knowledge agent (knowledge)
Retrieval-grounded answers + citations + DDG fallback + `needs_help`/gap. Depends on Slice 2 interfaces only (fake retriever in tests).
Checkpoint: knowledge unit tests green; demo against real index (waits for ingest only here).

### Slice 4 — Support agent (support)
Tool registry, 4-step bounded loop, mock bank data, "user not found", `tools_used`. No rag dependency → built **while ingest still runs**.
Checkpoint: support unit tests green; demo shows settlement-date answer.

### Slice 5 — Supervisor loop (router + graph)
LangGraph `StateGraph` (route/knowledge/support/triage nodes), intent classification, gap ledger, `GapExhausted`, 2-pass edge cap, triage, `FinalResponse` envelope.
Checkpoint: loop tests green (pass cap, repeated gap → triage, trace order).

### Slice 6 — HTTP surface (api)
`POST /chat`, `/health`, lifespan warm-up; TestClient contract tests with faked orchestrator.
Checkpoint: api tests green; local uvicorn smoke with curl.

### Slice 7 — Container (container-v2)
Dockerfile + compose + Makefile + `.env.example`; stale-image purge; warm boot; volumes verified across restart.
Checkpoint: `make run` → `/health` 200; restart → no model re-download.

### Slice 8 — Real HTTP smoke + docs (http-smoke)
10-scenario smoke script against compose; README.
Checkpoint: all 10 scenarios pass; README covers build/run/tests/architecture.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| torch/chromadb/sentence-transformers cp314 wheel gaps | High | Lock pins in Slice 1 (`uv add 'pkg==ver'` resolves); if a pin fails, surface immediately rather than improvising |
| F2LLM-v2-0.6B slow on CPU at ingest (~18 URLs) | Medium | Batch 8, ingest in background, log per-URL timing; index readiness only blocks Slice 3 demo, not implementation |
| Getnet pages block plain scrapers (403/JS-only) | Medium | Browser-like UA; cache raw HTML in `data/raw/`; if a page fails, log and continue — index degrades gracefully |
| LangGraph/LangChain API churn between versions | Medium | Pin exact versions at Slice 1; use only stable APIs (`StateGraph`, `add_conditional_edges`, `init_chat_model`, `@tool`); fake chat models in tests so behavior is pinned by contract, not by framework internals |
| `json_mode` unsupported by endpoint | Medium | Client fallback: retry without `response_format`; strict pydantic parse of agent outputs with 1 retry |
| ddgs rate limits / no results | Low | On failure or empty → treat as no web context; knowledge falls to `needs_help` per contract |
| Endpoint returns JSON that violates agent schema | Medium | One repair retry per LLM call (schema error fed back); then `needs_help`/triage path |
| Stale images reused by compose (postmortem) | Low | Makefile `run` target purges before `up` |

## Dependency Pins (locked at Slice 1 via uv)
`fastapi`, `uvicorn`, `httpx`, `pydantic`, `pydantic-settings`, `chromadb`, `sentence-transformers` (≥5, verified API), `torch` (cpu index, cp314 verified), `ddgs`, `beautifulsoup4`, `html2text`, `langchain`, `langchain-openai`, `langgraph`, dev: `pytest`. Exact `==` versions recorded in `pyproject.toml` + `uv.lock`; torch index declared via `[[tool.uv.index]]` (no `--torch-backend` flag — forbidden).

## Parallelization
- Background: real ingest (after Slice 2) runs unattended.
- Sequential-safe: Slices 3–6 are small; single-agent implementation is fine. `support` (4) is explicitly independent of `rag` and can precede/follow `knowledge` (3) without rework.

## Task List
Detailed, gated task breakdown with acceptance criteria and verification lives in `tasks/todo.md` (Phase 3 output).

## Open Questions
None — proceed to task breakdown on approval.
