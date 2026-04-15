import pytest

from docstruct.config import AgentConfig
from docstruct.infrastructure.llm import factory


def test_agent_config_uses_openai_model_when_provider_is_openai(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("DOCSTRUCT_AGENT_PROVIDER", raising=False)
    monkeypatch.delenv("DOCSTRUCT_AGENT_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")

    config = AgentConfig.from_env()

    assert config.provider == "openai"
    assert config.model == "gpt-4.1"


def test_build_client_requires_openai_api_key(monkeypatch, capsys):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        factory.build_client()

    assert exc_info.value.code == 3
    assert "OPENAI_API_KEY not set" in capsys.readouterr().err


def test_build_client_returns_openai_adapter(monkeypatch):
    class DummyAdapter:
        def __init__(self, *, api_key: str):
            self.api_key = api_key

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(factory, "OpenAIAdapter", DummyAdapter)

    client = factory.build_client()

    assert isinstance(client, DummyAdapter)
    assert client.api_key == "test-key"


def test_agent_config_uses_ollama_model_when_provider_is_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("DOCSTRUCT_AGENT_PROVIDER", raising=False)
    monkeypatch.delenv("DOCSTRUCT_AGENT_MODEL", raising=False)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    config = AgentConfig.from_env()

    assert config.provider == "ollama"
    assert config.model == "qwen3:8b"
    assert config.api_endpoint == "http://localhost:11434"


def test_build_client_returns_ollama_adapter(monkeypatch):
    class DummyAdapter:
        def __init__(self, *, base_url: str | None = None):
            self.base_url = base_url

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setattr(factory, "OllamaAdapter", DummyAdapter)

    client = factory.build_client()

    assert isinstance(client, DummyAdapter)
    assert client.base_url == "http://localhost:11434"
