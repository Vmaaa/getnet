# Capability Map: Getnet Multi-Agent Support System (MVP)

| Module id | Responsibility | Depends on |
|---|---|---|
| `platform` | Project skeleton, env config, structured logging, model-agnostic chat-model factory (LangChain `get_chat_model()`, provider env-swappable), shared domain contracts (`AgentResult{status, answer, gap}`, `Citation{ref, url, title, text}`) | — |
| `rag` | Ingestion pipeline (crawl fixed URL list → HTML→markdown → heading-aware chunks ~900 chars/15% overlap, breadcrumbs+lang+URL metadata) + embedded Chroma store (named volume) + retrieval (F2LLM-v2-0.6B `encode_query`/`encode_document`, cosine, top-k) | `platform` |
| `knowledge` | Knowledge agent: retrieve → grounded answer with exact-passage citations; `needs_help` + gap when context insufficient; web-search tool (DDG) for general-purpose questions | `platform`, `rag` |
| `support` | Support agent: bounded tool loop (max 4 steps) over `get_user_profile`, `get_transactions` (settlement dates), `get_device_status` on deterministic mock data; "user not found" outcome; `tools_used` from actual execution | `platform` |
| `router` | Router agent: classify intent, pick agent/sequence, re-plan on `needs_help` with gap injected, never re-plan with a repeated gap | `platform`, `knowledge`, `support` |
| `graph` | LangGraph `StateGraph` supervisor: nodes route/knowledge/support/triage, max 2 passes enforced in edge code, exhaustion → triage response, assembles final response (answer, citations, tools_used, trace) | `router` |
| `api` | FastAPI `POST /chat` (`{message, user_id}`), response with `answer`, `citations`, `tools_used`, `agent_trace`; health endpoint | `graph` |
| `container-v2` | Dockerfile (python 3.14-slim + uv 0.13.8, verified flags only) + compose with named volumes (chroma, hf-cache), embedding warm-up at start | `api`, `rag` |
| `http-smoke` | Real HTTP smoke test against the running compose stack (all 10 example scenarios) | `container-v2` |

## Build order

```
platform → rag → knowledge → support → router → graph → api → container-v2 → http-smoke
                    (support depends only on platform; may proceed in
                     parallel with knowledge but is sequenced after it)
```

## Cross-module contracts (owned by the provider module)

- `platform` owns: `AgentResult`, `Citation`, LLM client, config, logging conventions.
- `rag` owns: chunk schema, metadata schema (`url`, `title`, `lang`, `breadcrumbs`), retrieval interface returning passages with provenance.
- `knowledge`/`support` own: the `{status, answer, gap}` result contract, gap phrasing rules.
- `router` owns: intent taxonomy, re-plan semantics, gap-dedup ledger (per session).
- `graph` owns: pass counter, triage fallback, final response envelope.
- `api` owns: HTTP request/response schemas (contract with the grader).

## Fixed decisions (from human answers, 2026-11-13)

1. Vector store: **Chroma embedded**, persistent dir in named volume, cosine space.
2. Embeddings: **`codefuse-ai/F2LLM-v2-0.6B`** via sentence-transformers, **CPU-only**, asymmetric `encode_query` / `encode_document`, 1024-dim, cosine similarity.
3. Sources: the exact 18-URL list (site.getnet.com.br PT + getnet.net/en) with **heading-aware chunking**. Web search: **DuckDuckGo** (no API key).
4. Runtime: **Python 3.14 + uv 0.13.8**, everything pinned `==`.
5. LLM: **OpenAI-compatible, env-configured** (`OPENAI_BASE_URL`, `OPENAI_API_KEY`, `CHAT_MODEL`), one `httpx` client.
6. Prompts and responses in **English**; no TDD; ingestion parallel, non-blocking.
7. Orchestration: **LangGraph** `StateGraph` for inter-agent control transfer (pass cap + gap checks live in conditional-edge functions). Agents: **LangChain**, model-agnostic via `get_chat_model()` (`init_chat_model` with `llm_provider`/`chat_model` env; default provider `openai` covers any OpenAI-compatible endpoint through `base_url`).
