"""LLM provider configuration form.

Renders a Streamlit form that mirrors ``reveilio.configure(...)`` kwargs for
every supported provider and wires the submit action to the actual call.
"""

from __future__ import annotations

import streamlit as st

import reveilio

PROVIDERS = ["gemini", "openai", "azure", "ollama"]

_DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "azure": "gpt-4o",
    "ollama": "llama3.2",
}


def render_provider_form() -> None:
    """Render the provider configuration form and apply it on submit."""
    st.subheader("LLM provider")
    provider = st.selectbox(
        "Provider",
        PROVIDERS,
        index=0,
        help="Pick the LLM backend reveilio should use for scoring.",
    )

    with st.form("provider_form", clear_on_submit=False):
        kwargs: dict[str, object] = {"provider": provider}

        if provider == "gemini":
            kwargs["api_key"] = st.text_input("API key", type="password", placeholder="AIza…")
            kwargs["model"] = st.text_input("Model", value=_DEFAULT_MODELS["gemini"])

        elif provider == "openai":
            kwargs["api_key"] = st.text_input("API key", type="password", placeholder="sk-…")
            kwargs["model"] = st.text_input("Model", value=_DEFAULT_MODELS["openai"])

        elif provider == "azure":
            kwargs["api_key"] = st.text_input("API key", type="password")
            kwargs["azure_endpoint"] = st.text_input(
                "Azure endpoint",
                placeholder="https://your-resource.openai.azure.com/",
            )
            kwargs["azure_deployment"] = st.text_input(
                "Deployment name",
                value=_DEFAULT_MODELS["azure"],
            )
            kwargs["api_version"] = st.text_input("API version", value="2024-08-01-preview")

        elif provider == "ollama":
            kwargs["base_url"] = st.text_input(
                "Base URL",
                value="http://host.docker.internal:11434",
                help="Use host.docker.internal on macOS/Windows to reach an Ollama running on the host.",
            )
            kwargs["model"] = st.text_input("Model", value=_DEFAULT_MODELS["ollama"])

        submitted = st.form_submit_button("Save configuration")

    if submitted:
        clean = {k: v for k, v in kwargs.items() if v not in (None, "")}
        try:
            reveilio.configure(**clean)  # type: ignore[arg-type]
        except Exception as e:  # noqa: BLE001 — surface any config error to the UI
            st.error(f"Configuration failed: {e}")
            return
        st.session_state.llm_configured = True
        st.session_state.llm_provider = provider
        st.success(f"Configured provider: {provider}")
