import chromadb

from app.rag.chunking import Chunk
from app.rag.store import chunk_id, query, upsert_chunks


def fake_embed(texts: list[str]) -> list[list[float]]:
    return [[float(len(t) % 10), float(t.count("a")), 1.0, 0.0] for t in texts]


def _collection(tmp_path):
    client = chromadb.PersistentClient(
        path=str(tmp_path / "chroma"),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )
    return client.get_or_create_collection(name="test_docs", metadata={"hnsw:space": "cosine"})


def _chunk(url, index, text):
    return Chunk(text=text, url=url, title="T", lang="pt-BR", breadcrumbs="D > S", chunk_index=index)


def test_chunk_id_deterministic():
    assert chunk_id("u", 0) == chunk_id("u", 0)
    assert chunk_id("u", 0) != chunk_id("u", 1)


def test_upsert_and_query_roundtrip(tmp_path):
    col = _collection(tmp_path)
    chunks = [
        _chunk("https://site.getnet.com.br/pix", 0, "pix settlement rules a"),
        _chunk("https://site.getnet.com.br/pix", 1, "pix limits info aa"),
    ]
    n = upsert_chunks(col, chunks, fake_embed([c.text for c in chunks]))
    assert n == 2
    passages = query(col, fake_embed(["pix settlement rules"])[0], k=2)
    assert len(passages) == 2
    assert passages[0].url == "https://site.getnet.com.br/pix"
    assert passages[0].title == "T"
    assert passages[0].breadcrumbs == "D > S"
    assert all(p.score <= 1.0 for p in passages)


def test_upsert_length_mismatch(tmp_path):
    col = _collection(tmp_path)
    chunks = [_chunk("u", 0, "text a")]
    try:
        upsert_chunks(col, chunks, fake_embed(["a", "b"]))
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_upsert_idempotent(tmp_path):
    col = _collection(tmp_path)
    chunks = [_chunk("u", 0, "text a")]
    upsert_chunks(col, chunks, fake_embed([c.text for c in chunks]))
    upsert_chunks(col, chunks, fake_embed([c.text for c in chunks]))
    assert col.count() == 1
