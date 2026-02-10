"""
LLM factory — creates the right LangChain chat model based on config.
"""

from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import LLM_MODEL, LLM_PROVIDER, LLM_TEMPERATURE, OLLAMA_BASE_URL


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
        from langchain_google_genai import ChatGoogleGenerativeAI

        # browser_use 0.11.9 expects its own BaseChatModel protocol with
        # provider, model_name, and name attrs, and monkey-patches ainvoke
        # for token tracking.  ChatGoogleGenerativeAI (Pydantic extra='ignore')
        # has none of these and blocks setattr.  Subclass to bridge the gap.
        class _PatchableChatGoogle(ChatGoogleGenerativeAI):
            model_config = {"extra": "allow"}
            provider: str = "google"
            model_name: str = ""

        def _init_patchable(model_str: str, temperature: float) -> _PatchableChatGoogle:
            llm = _PatchableChatGoogle(model=model_str, temperature=temperature)
            # model_name must mirror model; set after init since model is
            # validated during __init__.
            object.__setattr__(llm, "model_name", llm.model)
            return llm

        return _init_patchable(LLM_MODEL, LLM_TEMPERATURE)

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
