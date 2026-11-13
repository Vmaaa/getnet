import argparse
import logging

from app.config import get_settings
from app.logging import configure_logging
from app.rag.chunking import split_markdown
from app.rag.crawl import crawl_all
from app.rag.embedder import embed_documents, get_embedder
from app.rag.store import get_collection, upsert_chunks

logger = logging.getLogger(__name__)


def run_ingest(reset: bool = False) -> int:
    collection = get_collection()
    if reset:
        existing = collection.get()["ids"]
        if existing:
            collection.delete(ids=existing)
        logger.info("collection reset documents=%d", len(existing))
    pages = crawl_all()
    model = get_embedder()
    total = 0
    for page in pages:
        chunks = split_markdown(page.markdown, page.url)
        if not chunks:
            logger.warning("no chunks url=%s", page.url)
            continue
        embeddings = embed_documents(model, [c.text for c in chunks])
        total += upsert_chunks(collection, chunks, embeddings)
        logger.info("ingested url=%s chunks=%d", page.url, len(chunks))
    logger.info("ingest complete total_chunks=%d collection_count=%d", total, collection.count())
    return total


def main() -> None:
    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    run_ingest(reset=args.reset)


if __name__ == "__main__":
    main()
