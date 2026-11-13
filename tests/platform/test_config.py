from app.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.chat_model == "gpt-4o-mini"
    assert s.llm_provider == "openai"
    assert s.rag_top_k == 5
    assert s.rag_min_score == 0.3
    assert s.embedding_model == "codefuse-ai/F2LLM-v2-0.6B"
    assert s.chroma_dir == "data/chroma"


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("CHAT_MODEL", "glm-4.6")
    monkeypatch.setenv("RAG_TOP_K", "7")
    s = Settings(_env_file=None)
    assert s.chat_model == "glm-4.6"
    assert s.rag_top_k == 7


def test_get_settings_cached():
    from app.config import get_settings

    assert get_settings() is get_settings()
