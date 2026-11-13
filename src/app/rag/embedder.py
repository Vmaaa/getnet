import os
from functools import lru_cache

from app.config import get_settings


@lru_cache
def get_embedder():
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    os.environ.setdefault("HF_HOME", settings.hf_cache)
    model = SentenceTransformer(settings.embedding_model, device="cpu")
    return model


def embed_documents(model, texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    embeddings = model.encode_document(
        texts,
        batch_size=settings.embedding_batch_size,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def embed_query(model, query: str) -> list[float]:
    embeddings = model.encode_query(query, normalize_embeddings=True)
    return embeddings.tolist()
