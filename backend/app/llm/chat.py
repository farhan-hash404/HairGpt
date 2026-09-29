"""Chat-model providers behind one LangChain interface.

Gemini, OpenAI, Anthropic Claude and AWS Bedrock all return a LangChain
``BaseChatModel``, so every agent is provider-agnostic. ``LLM_PROVIDER=auto``
uses the first provider with credentials; with none, the agents run their
deterministic paths, which quote sources verbatim and cannot hallucinate.

Every call is bounded by a latency budget. The website aborts requests after
8 seconds, so a slow model must degrade to the deterministic answer rather
than hang the user.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.config import settings

log = logging.getLogger("hairgpt.llm")

T = TypeVar("T", bound=BaseModel)

_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")


@dataclass(frozen=True)
class ProviderInfo:
    provider: str  # gemini | openai | anthropic | bedrock | none
    model: str
    available: bool
    reason: str = ""


def _choice() -> str:
    choice = (settings.llm_provider or "auto").lower()
    if choice in ("mock", "none", "off"):
        return "none"
    if choice != "auto":
        return choice
    if settings.gemini_api_key:
        return "gemini"
    if settings.openai_api_key:
        return "openai"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.bedrock_model_id and (os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE")):
        return "bedrock"
    return "none"


def _build(provider: str) -> tuple[Any | None, ProviderInfo]:
    timeout = max(settings.llm_timeout_s, 1.0)
    try:
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            model = settings.llm_model or settings.gemini_model
            if not settings.gemini_api_key:
                return None, ProviderInfo(provider, model, False, "GEMINI_API_KEY not set")
            chat = ChatGoogleGenerativeAI(
                model=model, google_api_key=settings.gemini_api_key,
                temperature=0.2, timeout=timeout, max_retries=1,
            )
            return chat, ProviderInfo(provider, model, True)
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            model = settings.llm_model or settings.openai_model
            if not settings.openai_api_key:
                return None, ProviderInfo(provider, model, False, "OPENAI_API_KEY not set")
            # GPT-5-family reasoning models accept only the default temperature.
            chat = ChatOpenAI(model=model, api_key=settings.openai_api_key, timeout=timeout, max_retries=1)
            return chat, ProviderInfo(provider, model, True)
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            model = settings.llm_model or settings.anthropic_model
            if not settings.anthropic_api_key:
                return None, ProviderInfo(provider, model, False, "ANTHROPIC_API_KEY not set")
            chat = ChatAnthropic(
                model=model, api_key=settings.anthropic_api_key,
                temperature=0.2, timeout=timeout, max_retries=1, max_tokens=1200,
            )
            return chat, ProviderInfo(provider, model, True)
        if provider == "bedrock":
            from langchain_aws import ChatBedrockConverse

            model = settings.llm_model or settings.bedrock_model_id or ""
            if not model:
                return None, ProviderInfo(provider, model, False, "BEDROCK_MODEL_ID not set")
            chat = ChatBedrockConverse(model=model, region_name=settings.aws_region, temperature=0.2)
            return chat, ProviderInfo(provider, model, True)
    except Exception as exc:  # missing package, bad credentials format, etc.
        log.warning("LLM provider %s unavailable: %s", provider, exc)
        return None, ProviderInfo(provider, settings.llm_model, False, str(exc))
    return None, ProviderInfo("none", "", False, "no LLM configured; deterministic mode")


@lru_cache(maxsize=1)
def get_chat_model() -> tuple[Any | None, ProviderInfo]:
    return _build(_choice())


def provider_info() -> ProviderInfo:
    return get_chat_model()[1]


def reset_chat_model() -> None:
    get_chat_model.cache_clear()


class LLMUnavailable(RuntimeError):
    """The model is absent, failed, or ran out of latency budget. Callers must
    fall back to their deterministic path."""


def invoke_structured(schema: type[T], system: str, user: str, timeout: float | None = None) -> T:
    """Call the configured model for a schema-validated object, within budget.

    Raises LLMUnavailable on any failure — callers never see a half answer.
    """
    chat, info = get_chat_model()
    if chat is None:
        raise LLMUnavailable(info.reason or "no LLM configured")
    structured = chat.with_structured_output(schema)
    future = _POOL.submit(structured.invoke, [("system", system), ("human", user)])
    try:
        result = future.result(timeout=timeout or settings.llm_timeout_s)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise LLMUnavailable(f"{info.provider} exceeded the {timeout or settings.llm_timeout_s:.0f}s budget") from exc
    except Exception as exc:
        raise LLMUnavailable(f"{info.provider} call failed: {exc}") from exc
    if not isinstance(result, schema):
        raise LLMUnavailable(f"{info.provider} returned no structured output")
    return result
