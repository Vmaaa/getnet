# Spec: container-v2

## Objective
Rebuild packaging from scratch (previous attempt failed): Docker image on `python:3.14-slim` + `uv 0.13.8` with only verified flags, compose with named volumes (no bind mounts), embedding warm-up at boot. Runs the real HTTP API.

## Tech Stack (pinned, verified)
- Base: `python:3.14-slim`; uv copied from `ghcr.io/astral-sh/uv:0.13.8`.
- **Allowed uv flags (verified for 0.13.x):** `sync --frozen --no-dev`, `run`, `export`. **Forbidden:** `--torch-backend` (does not exist).
- torch CPU via pyproject: `[[tool.uv.index]] name="pytorch-cpu" url="https://download.pytorch.org/whl/cpu"` + `[tool.uv.sources] torch = { index = "pytorch-cpu" }` (verified mechanism; cp314 cpu wheels confirmed).
- Named volumes: `chroma-data` → `/data/chroma`, `hf-cache` → `/cache/hf` (`HF_HOME`).

## Commands
```
Purge stale images: podman image rm <dangling-image-id> -f   (or docker image prune -f)
Build:              podman compose build   (or docker compose build)
Up:                 podman compose up -d
Logs (warm-up):     podman compose logs -f app
Health:             curl -s localhost:8000/health
Down:               podman compose down
Tests:              manual + http-smoke module
```

## Project Structure
```
Dockerfile
compose.yml
.env.example          # OPENAI_BASE_URL, OPENAI_API_KEY, CHAT_MODEL
Makefile              # run/build/smoke targets; run purges stale images first
```

## Code Style
```dockerfile
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.8 /uv /uvx /usr/local/bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src ./src
COPY data ./data
ENV HF_HOME=/cache/hf \
    CHROMA_DIR=/data/chroma \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uv", "run", "--no-dev", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
- compose: single `app` service, `8000:8000`, named volumes `chroma-data:/data/chroma` and `hf-cache:/cache/hf`, `env_file: .env`, healthcheck `curl -f http://localhost:8000/health` (curl installed via apt in image).
- Warm-up lives in API lifespan (SPEC-api); the model (~1.2GB) downloads into `hf-cache` on first boot — expected in logs, never at request time.
- Chroma population: if `chroma-data` volume is empty, the app serves with 0 chunks and health reports it; ingestion is a separate exec: `podman compose exec app uv run python -m app.rag.ingest` (also documented in README).

## Testing Strategy
Manual verification steps, each recorded in the implementation task: (1) image builds from scratch with no cached layers of the old attempt; (2) container boots, warm-up logs appear, `/health` returns 200; (3) restart `compose down && up` → no model re-download (hf-cache volume works); (4) `data/` bind mount is absent from compose.

## Boundaries
- Always: `Makefile run` purges stale project images before `up`; `.env` gitignored, `.env.example` committed.
- Ask first: adding services to compose (vector DB server, cache...).
- Never: bind-mount anything a container writes to; use an unverified uv flag; bake `.env` into the image.

## Success Criteria
- Clean build from purged state; `curl localhost:8000/health` → 200 after warm-up; volumes persist across restarts; second boot does not re-download the model.

## Open Questions
None.
