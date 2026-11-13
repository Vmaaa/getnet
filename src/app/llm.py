from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import get_settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    from langchain.chat_models import init_chat_model

    settings = get_settings()
    full_kwargs = {
        "base_url": settings.openai_base_url,
        "api_key": settings.openai_api_key or "not-provided",
        "temperature": 0,
        "timeout": 60,
        "max_retries": 2,
    }
    try:
        return init_chat_model(
            settings.chat_model,
            model_provider=settings.llm_provider,
            **full_kwargs,
        )
    except TypeError:
        return init_chat_model(
            settings.chat_model,
            model_provider=settings.llm_provider,
            temperature=0,
        )
