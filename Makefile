DOCKER ?= podman

.PHONY: run build down ingest smoke test logs

run:
	-$(DOCKER) image prune -f
	$(DOCKER) compose up -d --build
	$(DOCKER) compose logs -f app

build:
	$(DOCKER) compose build

down:
	$(DOCKER) compose down

ingest:
	$(DOCKER) compose exec app uv run python -m app.rag.ingest

smoke:
	uv run python scripts/smoke_http.py --base-url http://localhost:8000

test:
	uv run pytest -q

logs:
	$(DOCKER) compose logs -f app
