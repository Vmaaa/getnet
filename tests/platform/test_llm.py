from app.config import get_settings
from app.llm import get_chat_model


def test_get_chat_model_cached():
    assert get_chat_model() is get_chat_model()


def test_get_chat_model_configuration():
    settings = get_settings()
    model = get_chat_model()
    assert hasattr(model, "invoke")
    name = getattr(model, "model_name", None) or getattr(model, "model", None)
    assert name == settings.chat_model
