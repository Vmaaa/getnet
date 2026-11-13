from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    llm_provider: str = "openai"

    rag_top_k: int = 5
    rag_min_score: float = 0.3
    embedding_model: str = "codefuse-ai/F2LLM-v2-0.6B"
    embedding_batch_size: int = 8

    chroma_dir: str = "data/chroma"
    hf_cache: str = "data/hf_cache"

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
