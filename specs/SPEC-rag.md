# Spec: rag

## Objective
Ingest the fixed Getnet URL list → HTML → markdown → heading-aware chunks → F2LLM-v2-0.6B embeddings → embedded Chroma (cosine), and expose retrieval returning passages with provenance. Chunks are never rewritten downstream (citation law).

## Tech Stack
- `sentence-transformers` **v5.x** (verified: `encode_query`/`encode_document` are v5 API), `torch` CPU (verified: cp314 wheels exist, e.g. `torch==2.9.1+cpu` line), `chromadb` (embedded, `PersistentClient`), `httpx`, `beautifulsoup4` + `html2text`. Model: `codefuse-ai/F2LLM-v2-0.6B`, **device cpu**, 1024-dim, cosine.

## Fixed inputs
18 URLs (site.getnet.com.br PT-BR: todas-as-maquininhas, get-tap, link-de-pagamento, getcheckout, conta-digital, pix, crediario, emprestimo, pagamentos-recorrentes, split, tef, eye, duvidas; getnet.net/en: in-person-payments, online-payments, omnichannel, value-added-solutions). Constant `SOURCE_URLS` in code.

## Commands
```
Ingest:  uv run python -m app.rag.ingest --reset
Probe:   uv run python -m app.rag.probe "What is the difference between Get Clássica and Get Smart?"
Tests:   uv run pytest tests/rag -q
```

## Project Structure
```
src/app/rag/
  sources.py     # SOURCE_URLS
  crawl.py       # fetch + html->markdown, raw cache under data/raw/
  chunking.py    # heading-aware splitter
  embedder.py    # get_embedder() cached SentenceTransformer(cpu)
  store.py       # Chroma collection upsert/query wrapper
  retriever.py   # retrieve(query, k) -> list[Passage]
  ingest.py      # CLI: crawl -> chunk -> embed -> upsert
  probe.py       # CLI: print top-k passages
tests/rag/
```

## Code Style
```python
def split_markdown(md: str, max_chars: int = 900, overlap_chars: int = 135) -> list[Chunk]: ...
```
- Splitter: walk ATX headings (`#`..`####`); each section accumulates paragraphs into chunks ≤ `max_chars`; oversized sections continue with ~`overlap_chars` carried from previous chunk; each chunk carries `breadcrumbs` string (`"H1 > H2 > H3"`), `title` (H1), `url`, `lang` (`"en"` if `/en/` in URL else `"pt-BR"`), `chunk_index`.
- Embeddings: `encode_document(texts, normalize_embeddings=True)` at ingest; `encode_query(query, normalize_embeddings=True)` at query time. Batch 16.
- Chroma: collection `getnet_docs`, `hnsw:space=cosine`; metadata `{url, title, lang, breadcrumbs, chunk_index}`; deterministic ids `sha1(url + chunk_index)`.
- `retrieve(query, k)` returns `list[Passage]` (`text`, `url`, `title`, `lang`, `breadcrumbs`, `score`), sorted by score desc. `Passage` defined in `app.contracts`.
- Embedding injection: store/retriever accept an `EmbedFn` protocol so tests run without loading the 0.6B model.

## Testing Strategy
pytest unit tests: chunker (size caps, overlap, breadcrumbs, PT/EN lang tagging), store round-trip with fake embeddings (in-memory Chroma), retriever ordering + k. No test loads the real model.

## Boundaries
- Always: run ingest with `--reset` only when sources changed; log chunk count per URL.
- Ask first: changing chunk schema/metadata keys (container volume already holds data); adding URLs.
- Never: rewrite or truncate chunk text during retrieval; use `encode()` instead of the asymmetric `encode_query`/`encode_document` pair; write Chroma from anywhere but `store.py`.

## Testing note (ingestion is parallel)
Ingest runs as a background process during implementation. Other modules must not block on it; only `knowledge` eventually requires the populated index.

## Success Criteria
- Ingest completes over all 18 URLs; chunk texts ≤ ~1000 chars; probe returns passages whose text contains "Get Smart"/"Clássica" content for the difference question and matching content for antecipação/Pix/payment-link questions.
- Retrieval for a weather-type query returns low-score (irrelevant) passages — evidence grounding check will fire.

## Open Questions
None.
