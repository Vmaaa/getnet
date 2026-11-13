# Constitution — AI Hardcore Engineer: Multi-Agent Support System

Non-negotiable principles. Every spec, plan, and task traces to these. Amendments require explicit human approval.

## 1. Gated SDD flow

- Flow: constitution → capability map → module specs → plan → tasks → implementation.
- **No phase advances without explicit human approval.** Spec docs live in `specs/`.
- No code is written before the relevant module spec is approved.

## 2. Runtime and dependencies (pinned exactly)

- Python **3.14** (image `python:3.14-slim`), package manager **uv 0.13.8** (`ghcr.io/astral-sh/uv:0.13.8`).
- All dependencies pinned `==` in `pyproject.toml`, resolved through `uv.lock`.
- **Every flag written into a Dockerfile must be verified to exist in the pinned tool version** (lesson: `uv sync --torch-backend=cpu` does not exist in uv 0.13.x).
- Torch CPU: installed with the CPU index URL explicitly configured, not a nonexistent flag.

## 3. Single LLM access point

- Exactly one chat-model factory: `app.llm.get_chat_model()` (LangChain `init_chat_model`), configured via env: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL`, `LLM_PROVIDER` (default `openai`, which covers any OpenAI-compatible endpoint through `base_url`).
- Agents never call providers directly; they call the factory.
- **All agent prompts and user-facing responses are written in English**, regardless of the language of the underlying data (PT/EN).

## 4. Behavioral contracts are law

These are enforced in code, not by prompt alone:

1. **Supervisor feedback loop**: knowledge and support agents return `{status: answered|needs_help, answer, gap}`. On `needs_help`, the router re-plans with the gap injected. **The same gap never appears twice in one session.** Max **2 passes**, enforced in graph code. Exhaustion → triage response.
2. **Support agent**: bounded tool loop, max **4 steps**. Tools: `get_user_profile`, `get_transactions` (with settlement dates), `get_device_status`. Unknown user → explicit "user not found" outcome, never an unhandled exception. `tools_used` reflects **actual executed tools only**.
3. **Citations**: each citation is `{ref, url, title, text}` where `text` is the **exact retrieved passage** (verbatim, no rewriting). Refs `1..k` mirror exactly what the model saw in its context. Citations flow through to the HTTP response.
4. **Grounding**: knowledge answers come only from retrieved context or web-search results. No retrieved support for an answer → `needs_help` with a gap, never a hallucinated answer.

## 5. Container and data rules (from previous-attempt postmortem)

- **Delete stale images from earlier attempts before the first `compose up`** — the compose provider reuses them silently.
- **No bind mounts** for anything containers write. Named volumes for: Chroma persistent dir, HuggingFace/model cache.
- **Warm up the embedding model at container start** (~1.2 GB downloads silently on first use; never let the first user request pay that cost).
- CPU-only everywhere: no CUDA, no GPU flags.

## 6. Engineering rules

- **No TDD.** Tests exist and run (pytest), but development is not test-first.
- **Embedding/ingestion runs in the background** and never blocks spec implementation until a module genuinely needs the index.
- Modular boundaries per capability map; dependencies point one way, no cycles.
- Structured logs per agent turn (agent, status, gap, tools_used, latency) — MVP observability.

## 7. MVP scope fence

- In: platform → rag → knowledge → support → router → graph → api → container-v2 → http-smoke.
- Out (bonus track, not built now): guardrails agent, human escalation/Teams agent, dashboards, eval harness. The triage response is the handoff stub.
