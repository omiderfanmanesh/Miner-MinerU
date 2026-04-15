"""Ollama implementation of the LLM port."""

from __future__ import annotations

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover
    ChatOllama = None

from docstruct.infrastructure.llm.langchain_adapter import LangChainChatAdapter


class OllamaAdapter(LangChainChatAdapter):
    def __init__(self, *, base_url: str | None = None):
        if ChatOllama is None:
            raise ImportError("langchain-ollama package not installed")
        self._base_url = base_url

    def _build_model(self, *, model: str, max_tokens: int):
        kwargs = {
            "model": model,
            "temperature": 0,
            "num_predict": max_tokens,
        }
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return ChatOllama(**kwargs)
