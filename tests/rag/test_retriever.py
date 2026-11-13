import chromadb

from app.rag.chunking import Chunk
from app.rag.retriever import retrieve
from app.rag.store import upsert_chunks


def fake_embed(texts: list[str]) -> list[list[float]]:
    return [[float(len(t) % 10), float(t.count("a")), 1.0, 0.0] for t in texts]


def _collection(tmp_path):
    client = chromadb.PersistentClient(
        path=str(tmp_path / "chroma"),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name="test_docs", metadata={"hnsw:space": "cosine"})


def _chunk(url, index, text):
    return Chunk(text=text, url=url, title="T", lang="pt-BR", breadcrumbs="D", chunk_index=index)


def test_retrieve_respects_k_and_orders(tmp_path):
    col = _collection(tmp_path)
    chunks = [
        _chunk("u0", 0, "aaaa " * 30),
        _chunk("u1", 1, "a " * 40),
        _chunk("u2", 2, "bbbb " * 20),
    ]
    upsert_chunks(col, chunks, fake_embed([c.text for c in chunks]))
    q_vector = fake_embed(["a"])[0]
    passages = retrieve("a", k=2, collection=col, embed_query_fn=lambda t: q_vector)
    assert len(passages) == 2
    assert passages[0].score >= passages[1].score


def test_retrieve_empty_collection(tmp_path):
    col = _collection(tmp_path)
    assert retrieve("anything", collection=col, embed_query_fn=lambda t: [0.0]) == []


def test_retrieve_caps_k_at_count(tmp_path):
    col = _collection(tmp_path)
    chunks = [_chunk("u0", 0, "aaaa a")]
    upsert_chunks(col, chunks, fake_embed([c.text for c in chunks]))
    passages = retrieve("a", k=10, collection=col, embed_query_fn=lambda t: fake_embed([t])[0])
    assert len(passages) == 1
