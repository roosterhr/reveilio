"""LLM client dispatch for Gemini, OpenAI, Azure OpenAI, and Ollama.

Ported from the original backend's ``dynamic_llm.py`` but reads all
credentials from :class:`reveilio.config.ReveilioConfig` instead of
FastAPI settings.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from reveilio.config import ReveilioConfig, get_config

logger = logging.getLogger(__name__)


def json_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.1,
    response_json: bool = True,
    config: ReveilioConfig | None = None,
) -> str:
    """Run a single-shot completion and return the raw text/JSON string.

    The selected provider is read from :func:`reveilio.get_config`.
    """
    cfg = config or get_config()
    provider = cfg.provider

    if provider == "gemini":
        return _gemini(cfg, system_prompt, user_prompt, temperature, response_json)
    if provider == "openai":
        return _openai_like(
            cfg, system_prompt, user_prompt, temperature, response_json, azure=False
        )
    if provider == "azure":
        return _openai_like(cfg, system_prompt, user_prompt, temperature, response_json, azure=True)
    if provider == "ollama":
        return _ollama(cfg, system_prompt, user_prompt, temperature, response_json)

    raise ValueError(f"Unsupported provider: {provider}")


def _gemini(cfg, system_prompt, user_prompt, temperature, response_json) -> str:
    from google import genai
    from google.genai import types

    if not cfg.api_key:
        raise ValueError("Missing Gemini API key. Call reveilio.configure(api_key=...).")
    client = genai.Client(api_key=cfg.api_key)
    resp = client.models.generate_content(
        model=cfg.resolved_model(),
        contents=f"{system_prompt}\n\n{user_prompt}",
        config=types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json" if response_json else None,
        ),
    )
    return resp.text or ""


def _openai_like(
    cfg, system_prompt, user_prompt, temperature, response_json, *, azure: bool
) -> str:
    import openai

    if azure:
        if not (cfg.api_key and cfg.azure_endpoint and cfg.azure_deployment):
            raise ValueError("Azure OpenAI requires api_key, azure_endpoint, and azure_deployment.")
        client = openai.AzureOpenAI(
            api_key=cfg.api_key,
            azure_endpoint=cfg.azure_endpoint,
            api_version=cfg.azure_api_version,
        )
        model = cfg.azure_deployment
    else:
        if not cfg.api_key:
            raise ValueError("Missing OpenAI API key. Call reveilio.configure(api_key=...).")
        client = openai.OpenAI(api_key=cfg.api_key)
        model = cfg.resolved_model()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    if response_json:
        kwargs["response_format"] = {"type": "json_object"}
    resp = client.chat.completions.create(**kwargs)
    return (resp.choices[0].message.content or "") if resp.choices else ""


def _ollama(cfg, system_prompt, user_prompt, temperature, response_json) -> str:
    base = (cfg.base_url or "http://localhost:11434").rstrip("/")
    url = f"{base}/api/chat"
    payload: dict[str, Any] = {
        "model": cfg.resolved_model() or "llama3.2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if response_json:
        payload["format"] = "json"
    with httpx.Client(timeout=120.0) as h:
        r = h.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    msg = data.get("message") or {}
    return msg.get("content") or ""
