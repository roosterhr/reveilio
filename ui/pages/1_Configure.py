"""Configure LLM provider and (optionally) a database backend."""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit runs each page file as a separate script; ensure the ui/
# parent is on sys.path so sibling `components` imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from branding import init_page  # noqa: E402
from components.db_form import render_db_form  # noqa: E402
from components.provider_form import render_provider_form  # noqa: E402

init_page(title="Configure | reveilio", icon="⚙️")
st.title("Configure")
st.caption("Set up your LLM provider and, optionally, a database connection.")

render_provider_form()
st.divider()
render_db_form()
