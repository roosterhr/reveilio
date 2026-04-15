"""Shared branding and page-init helpers for the reveilio UI."""

from __future__ import annotations

import base64
import urllib.request

import streamlit as st

LOGO_PATH = "https://raw.githubusercontent.com/roosterhr/reveilio/main/docs/assets/logo.png"


def _logo_path() -> str | None:
    return LOGO_PATH


def _logo_data_uri() -> str | None:
    try:
        with urllib.request.urlopen(LOGO_PATH, timeout=5) as resp:
            data = resp.read()
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return None


def init_page(title: str = "reveilio", icon: str = "📄") -> None:
    """Set page config and render the sidebar brand. Call once at the top of each page."""
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_sidebar_css()
    _render_sidebar_brand()


def _inject_sidebar_css() -> None:
    """Reorder the sidebar so our brand block renders above Streamlit's page nav."""
    st.markdown(
        """
        <style>
          section[data-testid="stSidebar"] > div:first-child {
              display: flex;
              flex-direction: column;
              padding-top: 0.5rem;
          }
          [data-testid="stSidebarNav"] {
              order: 2;
              padding-top: 0.5rem !important;
              margin-top: 0 !important;
          }
          [data-testid="stSidebarNav"] > ul { padding-top: 0 !important; }
          [data-testid="stSidebarUserContent"] {
              order: 1;
              padding-top: 0 !important;
              padding-bottom: 0 !important;
          }
          [data-testid="stSidebarUserContent"] hr {
              margin-top: 0.5rem !important;
              margin-bottom: 0.5rem !important;
          }
          .reveilio-brand {
              display: flex;
              align-items: center;
              gap: 0.6rem;
              padding: 0;
              margin: 0;
          }
          .reveilio-brand img {
              width: 36px;
              height: 36px;
              object-fit: contain;
              flex-shrink: 0;
          }
          .reveilio-brand .brand-text h1 {
              margin: 0;
              padding: 0;
              font-size: 1.35rem;
              line-height: 1.1;
              font-weight: 700;
          }
          .reveilio-brand .brand-text p {
              margin: 0;
              color: #64748b;
              font-size: 0.75rem;
              line-height: 1.2;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_brand() -> None:
    """Render logo + product name horizontally in the sidebar."""
    src = _logo_data_uri()
    img_tag = f'<img src="{src}" alt="reveilio" />' if src else ""
    st.sidebar.markdown(
        f"""
        <div class="reveilio-brand">
          {img_tag}
          <div class="brand-text">
            <h1>reveilio</h1>
            <p>Resume &times; JD matching</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.divider()


def render_landing_brand() -> None:
    """Prominent logo + title block for the main area of the landing page."""
    logo = _logo_path()
    cols = st.columns([1, 6])
    with cols[0]:
        if logo:
            st.image(logo, width=90)
    with cols[1]:
        st.title("reveilio")
        st.caption("AI-powered resume and job-description matching and scoring.")
