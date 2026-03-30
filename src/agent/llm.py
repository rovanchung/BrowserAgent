"""
LLM factory — creates the right LangChain chat model based on config.
"""

from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import (
    GCP_LOCATION,
    GCP_PROJECT,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    OLLAMA_BASE_URL,
    USE_VERTEX_AI,
)


def build_llm() -> BaseChatModel:
    """Instantiate a LangChain chat model from the user's settings.

    Supported providers: openai, anthropic, google, ollama.
    """

    provider = LLM_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
        )

    if provider == "google":
        from browser_use.llm.google import ChatGoogle

        kwargs = dict(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
        )
        if USE_VERTEX_AI:
            kwargs["vertexai"] = True
            if GCP_PROJECT:
                kwargs["project"] = GCP_PROJECT
            if GCP_LOCATION:
                kwargs["location"] = GCP_LOCATION
        return ChatGoogle(**kwargs)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            base_url=OLLAMA_BASE_URL,
        )

    raise ValueError(
        f"Unknown LLM_PROVIDER: {provider!r}. "
        "Supported: openai, anthropic, google, ollama"
    )
