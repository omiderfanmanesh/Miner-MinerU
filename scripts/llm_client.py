"""LLM client factory.

Reads LLM_PROVIDER from environment (default: anthropic).
Supports:
  - "anthropic": uses ANTHROPIC_API_KEY
  - "azure": uses AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
             AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION
"""
from __future__ import annotations

import os
import sys


def build_client():
    """Return a client object for the configured LLM provider.

    The returned client is passed to toc_extractor functions which call
    client.messages.create(...) for Anthropic, or we wrap Azure so it
    presents the same interface.
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if provider == "azure":
        return _build_azure_client()
    elif provider == "anthropic":
        return _build_anthropic_client()
    else:
        print(f"ERROR: Unknown LLM_PROVIDER={provider!r}. Must be 'anthropic' or 'azure'.", file=sys.stderr)
        sys.exit(3)


def _build_anthropic_client():
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(3)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(3)

    return anthropic.Anthropic(api_key=api_key)


def _build_azure_client():
    try:
        from openai import AzureOpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(3)

    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")

    if not api_key:
        print("ERROR: AZURE_OPENAI_API_KEY not set.", file=sys.stderr)
        sys.exit(3)
    if not endpoint:
        print("ERROR: AZURE_OPENAI_ENDPOINT not set.", file=sys.stderr)
        sys.exit(3)

    raw = AzureOpenAI(api_key=api_key, azure_endpoint=endpoint, api_version=api_version)
    return _AzureClientWrapper(raw, deployment)


class _AzureClientWrapper:
    """Wraps AzureOpenAI to present the same interface as anthropic.Anthropic.

    toc_extractor calls:
        client.messages.create(model=..., max_tokens=..., messages=[...])
    and reads:
        message.content[0].text

    This wrapper translates those calls to the OpenAI chat completions API.
    """

    def __init__(self, azure_client, deployment: str):
        self._client = azure_client
        self._deployment = deployment
        self.messages = _MessagesNamespace(azure_client, deployment)


class _MessagesNamespace:
    def __init__(self, azure_client, deployment: str):
        self._client = azure_client
        self._deployment = deployment

    def create(self, *, model: str, max_tokens: int, messages: list) -> "_AzureResponse":
        response = self._client.chat.completions.create(
            model=self._deployment,
            max_tokens=max_tokens,
            messages=messages,
        )
        return _AzureResponse(response)


class _AzureResponse:
    def __init__(self, openai_response):
        text = openai_response.choices[0].message.content or ""
        self.content = [_TextContent(text)]


class _TextContent:
    def __init__(self, text: str):
        self.text = text
