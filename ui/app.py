"""Streamlit landing page for the reveilio UI.

This file is packaged only inside the Docker image. It is NOT part of the
PyPI wheel (see pyproject.toml's ``[tool.hatch.build.targets.wheel]``).
"""

from __future__ import annotations

import streamlit as st

from branding import init_page, render_landing_brand

UI_VERSION = "0.1.1"

init_page(title="reveilio", icon="📄")


def _init_session_state() -> None:
    defaults = {
        "llm_configured": False,
        "llm_provider": None,
        "db_connected": False,
        "db_backend": None,
        "jd": None,
        "results": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state()

render_landing_brand()

left, right = st.columns([2, 1])

with left:
    st.markdown(
        """
        Reveilio scores resumes against a job description using an LLM of
        your choice, ranks candidates, and lets you persist results to a
        database and export professional PDF reports.

        **To get started**, open the **Configure** page in the sidebar and
        pick an LLM provider. Then head to **Analyze** to score resumes.
        """
    )

with right:
    st.subheader("Status")
    st.write(
        f"**LLM**: {'✅ ' + str(st.session_state.llm_provider) if st.session_state.llm_configured else '—'}"
    )
    st.write(
        f"**Database**: {'✅ ' + str(st.session_state.db_backend) if st.session_state.db_connected else '—'}"
    )
    st.write(f"**reveilio version**: `{UI_VERSION}`")

st.divider()

st.subheader("Workflow")
cols = st.columns(4)
steps = [
    (
        "1. Configure",
        "Pick an LLM provider (Gemini, OpenAI, Azure, or Ollama) and optionally connect a database.",
    ),
    (
        "2. Analyze",
        "Upload a job description and one or many resumes. Reveilio returns a ranked, scored list.",
    ),
    ("3. Database", "Browse, filter, and delete previously saved analyses."),
    ("4. Reports", "Download polished PDF reports for individual candidates or the full batch."),
]
for col, (title, body) in zip(cols, steps):
    with col:
        st.markdown(f"**{title}**")
        st.caption(body)
