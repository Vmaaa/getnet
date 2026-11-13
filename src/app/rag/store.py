import hashlib
import logging
from functools import lru_cache
from typing import Protocol

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.contracts import Passage
from app.rag.chunking import Chunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "getnet_docs"


class EmbedFn(Protocol):
    def __call__(self, texts: list[str]) -> list[list[float]]: ...


def chunk_id(url: str, chunk_index: int) -> str:
    return hashlib.sha1(f"{url}{chunk_index}".encode()).hexdigest()


@lru_cache
def get_collection(path: str | None = None):
    settings = get_settings()
    client = chromadb.PersistentClient(
        path=path or settings.chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(collection, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")
    collection.upsert(
        ids=[chunk_id(c.url, c.chunk_index) for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[
            {
                "url": c.url,
                "title": c.title,
                "lang": c.lang,
                "breadcrumbs": c.breadcrumbs,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ],
        embeddings=embeddings,
    )
    logger.info("upserted chunks=%d", len(chunks))
    return len(chunks)


def query(collection, query_embedding: list[float], k: int) -> list[Passage]:
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    passages: list[Passage] = []
    for text, meta, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
        strict=True,
    ):
        passages.append(
            Passage(
                text=text,
                url=meta["url"],
                title=meta["title"],
                lang=meta["lang"],
                breadcrumbs=meta["breadcrumbs"],
                score=1.0 - float(distance),
            )
        )
    return passages
