"""Process-global configuration for reveilio.

Users call :func:`configure` once (typically at program start) to set the
LLM provider and credentials. All downstream functions read from the
singleton returned by :func:`get_config`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal

Provider = Literal["gemini", "openai", "azure", "ollama"]

DEFAULT_WEIGHTS: dict[str, float] = {
    "skills": 0.20,
    "semantic_skills": 0.20,
    "experience": 0.25,
    "education": 0.15,
    "certifications": 0.10,
    "soft_skills": 0.05,
    "domain_relevance": 0.05,
}

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "azure": "",  # must be set to the Azure deployment name
    "ollama": "llama3.2",
}


@dataclass
class ReveilioConfig:
    """Runtime configuration for reveilio.

    Prefer creating one via :func:`configure` rather than instantiating directly.
    """

    provider: Provider = "gemini"
    api_key: str | None = None
    model: str | None = None

    # Azure-only
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    azure_api_version: str = "2024-02-15-preview"

    # Ollama-only
    base_url: str | None = None

    # Scoring tweaks
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    def resolved_model(self) -> str:
        if self.model:
            return self.model
        if self.provider == "azure":
            return self.azure_deployment or ""
        return DEFAULT_MODELS.get(self.provider, "")


_config: ReveilioConfig | None = None


def configure(
    provider: Provider,
    api_key: str | None = None,
    model: str | None = None,
    *,
    azure_endpoint: str | None = None,
    azure_deployment: str | None = None,
    azure_api_version: str = "2024-02-15-preview",
    base_url: str | None = None,
    weights: dict[str, float] | None = None,
) -> ReveilioConfig:
    """Configure reveilio's LLM provider.

    Any argument left as ``None`` falls back to environment variables:

    * ``GEMINI_API_KEY`` / ``OPENAI_API_KEY`` / ``AZURE_OPENAI_API_KEY``
    * ``AZURE_OPENAI_ENDPOINT`` / ``AZURE_OPENAI_DEPLOYMENT`` / ``AZURE_OPENAI_API_VERSION``
    * ``OLLAMA_BASE_URL``

    Examples::

        reveilio.configure(provider="gemini", api_key="AIza...")
        reveilio.configure(provider="openai", api_key="sk-...", model="gpt-4o-mini")
        reveilio.configure(
            provider="azure",
            api_key="...",
            azure_endpoint="https://my-rsrc.openai.azure.com",
            azure_deployment="gpt-4o",
        )
        reveilio.configure(provider="ollama", base_url="http://localhost:11434", model="llama3.2")
    """
    global _config

    provider = provider.lower()  # type: ignore[assignment]
    if provider not in ("gemini", "openai", "azure", "ollama"):
        raise ValueError(
            f"Unsupported provider {provider!r}. Use one of: gemini, openai, azure, ollama."
        )

    if api_key is None:
        api_key = _env_key_for(provider)
    if provider == "azure":
        azure_endpoint = azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_deployment = azure_deployment or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        azure_api_version = (
            azure_api_version
            or os.environ.get("AZURE_OPENAI_API_VERSION")
            or "2024-02-15-preview"
        )
    if provider == "ollama" and not base_url:
        base_url = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"

    _config = ReveilioConfig(
        provider=provider,  # type: ignore[arg-type]
        api_key=api_key,
        model=model,
        azure_endpoint=(azure_endpoint or "").rstrip("/") or None,
        azure_deployment=azure_deployment,
        azure_api_version=azure_api_version,
        base_url=(base_url or "").rstrip("/") or None,
        weights=dict(weights) if weights else dict(DEFAULT_WEIGHTS),
    )
    return _config


def get_config() -> ReveilioConfig:
    """Return the active config, raising if :func:`configure` was never called.

    As a convenience, if no ``configure()`` call has been made but an env var
    like ``GEMINI_API_KEY`` or ``OPENAI_API_KEY`` is present, a default config
    is created automatically.
    """
    global _config
    if _config is not None:
        return _config

    # Auto-detect from env as a last resort
    for provider in ("gemini", "openai", "azure", "ollama"):
        if _env_key_for(provider) or (provider == "ollama" and os.environ.get("OLLAMA_BASE_URL")):
            return configure(provider)  # type: ignore[arg-type]

    raise RuntimeError(
        "reveilio is not configured. Call reveilio.configure(provider=..., api_key=...) first."
    )


def _env_key_for(provider: str) -> str | None:
    mapping = {
        "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        "openai": ("OPENAI_API_KEY",),
        "azure": ("AZURE_OPENAI_API_KEY",),
        "ollama": (),
    }
    for var in mapping.get(provider, ()):
        val = os.environ.get(var)
        if val:
            return val
    return None
