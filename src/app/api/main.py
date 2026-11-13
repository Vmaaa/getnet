import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.schemas import ChatRequest
from app.config import get_settings
from app.graph.builder import Orchestrator, build_orchestrator
from app.graph.state import FinalResponse
from app.logging import configure_logging
from app.rag.embedder import get_embedder
from app.rag.store import get_collection

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chroma_chunks = getattr(app.state, "chroma_chunks", 0)
    app.state.embedder = getattr(app.state, "embedder", "not_loaded")
    if app.state.orchestrator is None:
        configure_logging(get_settings().log_level)
        get_embedder()
        app.state.embedder = "loaded"
        app.state.chroma_chunks = get_collection().count()
        app.state.orchestrator = build_orchestrator()
        logger.info("warm-up complete chroma_chunks=%d", app.state.chroma_chunks)
    yield


def create_app(orchestrator: Orchestrator | None = None) -> FastAPI:
    app = FastAPI(title="Getnet Multi-Agent Support", version="0.1.0", lifespan=lifespan)
    app.state.orchestrator = orchestrator

    @app.post("/chat", response_model=FinalResponse)
    def chat(req: ChatRequest) -> FinalResponse:
        return app.state.orchestrator.handle(req.message, req.user_id)

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "chroma_chunks": app.state.chroma_chunks,
            "embedder": app.state.embedder,
        }

    @app.exception_handler(Exception)
    async def unhandled(request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error path=%s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "internal error"})

    return app


app = create_app()
