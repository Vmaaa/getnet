# Task List — Getnet Multi-Agent Support System (MVP)

Plan: `tasks/plan.md`. Specs: `specs/`. Rules: constitution §4 contracts enforced in code; no TDD ordering (tests land with the task, not before); ingestion background rule applies from Task 6.

- [x] Task 1: Scaffold + pinned deps + config + logging
  - Acceptance: `pyproject.toml` with exact `==` pins (fastapi, uvicorn, httpx, pydantic, pydantic-settings, chromadb, sentence-transformers 5.x, torch cpu via `[[tool.uv.index]]`, ddgs, beautifulsoup4, html2text, langchain, langchain-openai, langgraph, pytest); `uv.lock` resolves on cp314; `get_settings()` loads `.env`; logging configured in one call.
  - Verify: `uv sync` succeeds; `uv run pytest tests/platform -q` green; `uv run python -c "from app.config import get_settings; print(get_settings().chat_model)"`.
  - Files: `pyproject.toml`, `.gitignore`, `src/app/__init__.py`, `src/app/config.py`, `src/app/logging.py`, `tests/platform/test_config.py`
  - Deps: none. Size: M
  - If any pin fails to resolve on cp314 → STOP and surface before improvising.

- [x] Task 2: Contracts + model factory
  - Acceptance: `Citation`, `AgentResult`, `Passage` pydantic models reject invalid statuses; `get_chat_model()` returns cached model configured with provider/base_url from settings (asserted without network).
  - Verify: `uv run pytest tests/platform -q` green.
  - Files: `src/app/contracts.py`, `src/app/llm.py`, `tests/platform/test_contracts.py`, `tests/platform/test_llm.py`
  - Deps: 1. Size: S

- [x] **Checkpoint A (foundation):** full `uv run pytest -q` green; pins locked; no orphan imports.

- [x] Task 3: Crawler + HTML→markdown
  - Acceptance: `SOURCE_URLS` (18 URLs) constant; fetch with browser-like UA; raw HTML + markdown cached under `data/raw/`; failures logged and skipped, never raised.
  - Verify: `uv run python -c "from app.rag.crawl import crawl_all; m = crawl_all(); print(len(m))"` runs (manual, network).
  - Files: `src/app/rag/__init__.py`, `src/app/rag/sources.py`, `src/app/rag/crawl.py`, `tests/rag/test_crawl.py` (fake transport)
  - Deps: 1. Size: M

- [x] Task 4: Heading-aware chunker
  - Acceptance: splits markdown on ATX headings; chunks ≤900 chars with 135-char carry-over overlap; `breadcrumbs`, `title`, `lang` (en/pt-BR), `chunk_index` metadata.
  - Verify: `uv run pytest tests/rag/test_chunking.py -q` green (real fixture markdown, no network).
  - Files: `src/app/rag/chunking.py`, `tests/rag/test_chunking.py`
  - Deps: 1. Size: S

- [x] Task 5: Embedder + Chroma store + retriever
  - Acceptance: `get_embedder()` cached (cpu, HF cache path); `store.py` upsert/query with cosine space + metadata, deterministic sha1 ids; `retrieve(query, k)` → `list[Passage]` with scores; `EmbedFn` injectable everywhere.
  - Verify: `uv run pytest tests/rag/test_store.py tests/rag/test_retriever.py -q` green with fake embeddings (in-memory Chroma).
  - Files: `src/app/rag/embedder.py`, `src/app/rag/store.py`, `src/app/rag/retriever.py`, `tests/rag/test_store.py`, `tests/rag/test_retriever.py`
  - Deps: 2, 4. Size: M

- [x] Task 6: Ingest + probe CLIs → launch background ingest
  - Acceptance: `uv run python -m app.rag.ingest --reset` runs crawl→chunk→embed→upsert with per-URL logs; `app.rag.probe` prints top-k with URLs.
  - Verify: launch ingest **in background** (`uv run python -m app.rag.ingest --reset`), continue Tasks 7+; probe on the real index only at Checkpoint C.
  - Files: `src/app/rag/ingest.py`, `src/app/rag/probe.py`
  - Deps: 3, 5. Size: S

- [x] **Checkpoint B (rag):** chunker/store/retriever tests green; background ingest running.

- [x] Task 7: KnowledgeAgent
  - Acceptance: retrieval → refs `1..k` context → structured-output decision → citations mirror context verbatim; DDG fallback on low score/general intent; `needs_help` + gap on insufficient context.
  - Verify: `uv run pytest tests/knowledge -q` green (fake retriever, fake chat model).
  - Files: `src/app/agents/__init__.py`, `src/app/agents/knowledge.py`, `src/app/agents/prompts/__init__.py`, `src/app/agents/prompts/knowledge.py`, `tests/knowledge/test_knowledge.py`
  - Deps: 5. Size: M

- [x] Task 8: Mock bank + tools
  - Acceptance: deterministic dataset (dates relative to today, D+1/D+2 settlement) for `cliente1988` + 2 others; three LangChain `@tool` defs returning JSON-safe dicts; unknown id → `None`.
  - Verify: `uv run pytest tests/support/test_tools.py -q` green.
  - Files: `data/mock_bank.py`, `src/app/agents/tools.py`, `tests/support/test_tools.py`
  - Deps: 2. Size: M

- [x] Task 9: SupportAgent (bounded tool loop)
  - Acceptance: LangGraph subgraph, model node + tool node, cap at 4 steps in edge function; `tools_used` from executed `ToolMessage`s; unknown user → "user not found"; exhaustion → `needs_help`.
  - Verify: `uv run pytest tests/support/test_support.py -q` green (scripted fake tool-calling model).
  - Files: `src/app/agents/support.py`, `src/app/agents/prompts/support.py`, `tests/support/test_support.py`, `tests/support/fakes.py`
  - Deps: 8. Size: M

- [x] **Checkpoint C (agents):** ingest finished → `probe "What is the difference between Get Clássica and Get Smart?"` returns relevant passages; knowledge + support tests green; manual demo of both agents.

- [x] Task 10: RouterAgent
  - Acceptance: intent classification via structured output + keyword fallback; dispatch returns `AgentResult` untouched; per-session gap ledger; `replan` raises `GapExhausted` on repeated gap.
  - Verify: `uv run pytest tests/router -q` green.
  - Files: `src/app/agents/router.py`, `src/app/agents/prompts/router.py`, `tests/router/test_router.py`
  - Deps: 7, 9. Size: M

- [x] Task 11: LangGraph supervisor + Orchestrator
  - Acceptance: `StateGraph` route/knowledge/support/triage nodes; `MAX_PASSES=2` + gap check in `after_agent` edge; `TraceEntry`s accumulate; triage envelope on exhaustion; `session_id` per handle.
  - Verify: `uv run pytest tests/graph -q` green (fake router/agents in builder).
  - Files: `src/app/graph/__init__.py`, `src/app/graph/state.py`, `src/app/graph/builder.py`, `src/app/graph/orchestrator.py`, `tests/graph/test_graph.py`
  - Deps: 10. Size: M

- [x] **Checkpoint D (local e2e):** scripted demo: `uv run python -m app.graph.demo` answers product, support, weather, and unanswerable questions locally.

- [x] Task 12: FastAPI surface
  - Acceptance: `POST /chat` validates `{message, user_id}` → `ChatResponse`; `/health` reports chunk count + embedder state; lifespan warm-up loads embedder + Chroma before serving; 422/500 paths.
  - Verify: `uv run pytest tests/api -q` green (TestClient + faked graph); local `uvicorn` curl smoke.
  - Files: `src/app/api/__init__.py`, `src/app/api/schemas.py`, `src/app/api/main.py`, `tests/api/test_api.py`
  - Deps: 11. Size: M

- [x] Task 13: Container v2
  - Acceptance: Dockerfile per SPEC-container-v2 (uv 0.13.8 binary copy, `sync --frozen --no-dev` only, torch cpu index in pyproject, HF_HOME/CHROMA_DIR env); compose with named volumes `chroma-data`, `hf-cache`, healthcheck; `.env.example`; Makefile `run` purges stale images first.
  - Verify: build starts clean (manual at Task 14).
  - Files: `Dockerfile`, `compose.yml`, `.env.example`, `Makefile`
  - Deps: 12. Size: M

- [x] Task 14: Container verification (manual, gated by postmortem rules)
  - Acceptance: stale images purged; build succeeds; boot → warm-up logs → `/health` 200; `compose down && up` → no model re-download (hf-cache volume); no bind mounts present.
  - Verify: `make run`; `curl -s localhost:8000/health`; restart persistence check.
  - Files: none (verification only)
  - Deps: 13. Size: S

- [x] **Checkpoint E (container):** real HTTP up with persistent volumes.

- [x] Task 15: HTTP smoke (10 scenarios)
  - Acceptance: all 10 challenge scenarios; per SPEC-http-smoke checks (200, schema, contiguous refs on knowledge, real tool names on support, trace integrity); table + non-zero exit on failure.
  - Verify: `uv run python scripts/smoke_http.py --base-url http://localhost:8000` exits 0.
  - Files: `scripts/smoke_http.py`
  - Deps: 14. Size: M

- [x] Task 16: README
  - Acceptance: build/config/run/test instructions; orchestration architecture + message workflow; RAG pipeline (ingest → storage → retrieval → generation); tool usage; testing strategy + smoke; observability notes (structured logs, trace envelope).
  - Verify: manual read-through against running stack commands.
  - Files: `README.md`
  - Deps: 15. Size: M

- [x] **Checkpoint F (complete):** all specs' success criteria demonstrated; smoke table green; repo ready for submission.
