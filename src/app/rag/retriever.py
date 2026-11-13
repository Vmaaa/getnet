import logging

from app.config import get_settings
from app.contracts import Passage
from app.rag.embedder import embed_query, get_embedder
from app.rag.store import get_collection
from app.rag.store import query as query_store

logger = logging.getLogger(__name__)


def _default_embed_query_fn(text: str) -> list[float]:
    return embed_query(get_embedder(), text)


def retrieve(
    query: str,
    k: int | None = None,
    *,
    collection=None,
    embed_query_fn=None,
) -> list[Passage]:
    settings = get_settings()
    k = k or settings.rag_top_k
    collection = collection if collection is not None else get_collection()
    embed_fn = embed_query_fn or _default_embed_query_fn
    count = collection.count()
    if count == 0:
        logger.warning("retrieval on empty collection")
        return []
    passages = query_store(collection, embed_fn(query), min(k, count))
    top = passages[0].score if passages else 0.0
    logger.info("retrieved query=%r k=%d top_score=%.3f", query[:80], len(passages), top)
    return passages
