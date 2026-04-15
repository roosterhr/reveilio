"""Database page: browse, filter, and delete stored analyses."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import reveilio  # noqa: E402
from branding import init_page  # noqa: E402
from components.results_table import render_results  # noqa: E402

init_page(title="Database | reveilio", icon="🗄️")
st.title("Database")

if not st.session_state.get("db_connected"):
    st.warning("Connect a database first (sidebar → Configure → Database).")
    st.stop()

st.caption(f"Active backend: **{st.session_state.db_backend}**")

tab_list, tab_query = st.tabs(["Browse", "Filter"])

with tab_list:
    st.subheader("Recent analyses")
    limit = st.number_input("Page size", min_value=5, max_value=500, value=50, step=5)
    page = st.number_input("Page (0-indexed)", min_value=0, value=0, step=1)

    try:
        entries = reveilio.list_analyses(limit=int(limit), offset=int(page) * int(limit))
    except Exception as e:  # noqa: BLE001
        st.error(f"Failed to load analyses: {e}")
        entries = []

    if not entries:
        st.info("No analyses stored yet.")
    else:
        st.dataframe(pd.DataFrame(entries), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Delete")
        aid = st.text_input("analysis_id to delete")
        if st.button("Delete", type="primary", disabled=not aid):
            try:
                deleted = reveilio.delete_result(aid)
                if deleted:
                    st.success(f"Deleted {aid}.")
                    st.rerun()
                else:
                    st.warning("No record with that id.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Delete failed: {e}")

with tab_query:
    st.subheader("Filter results")
    with st.form("query_form"):
        col1, col2 = st.columns(2)
        with col1:
            candidate_name = st.text_input("Candidate name contains")
            min_score = st.number_input(
                "Min score", min_value=0.0, max_value=100.0, value=0.0, step=1.0
            )
            max_score = st.number_input(
                "Max score", min_value=0.0, max_value=100.0, value=100.0, step=1.0
            )
        with col2:
            recommendation = st.selectbox(
                "Recommendation",
                ["(any)", "Shortlist", "Needs Review", "Not Suitable"],
            )
            job_title = st.text_input("Job title contains")
            result_limit = st.number_input("Limit", min_value=1, max_value=500, value=100, step=10)
        submitted = st.form_submit_button("Run query")

    if submitted:
        kwargs = {
            "limit": int(result_limit),
        }
        if candidate_name.strip():
            kwargs["candidate_name"] = candidate_name.strip()
        if min_score > 0:
            kwargs["min_score"] = float(min_score)
        if max_score < 100:
            kwargs["max_score"] = float(max_score)
        if recommendation != "(any)":
            kwargs["recommendation"] = recommendation
        if job_title.strip():
            kwargs["job_title"] = job_title.strip()

        try:
            results = reveilio.query_results(**kwargs)
        except Exception as e:  # noqa: BLE001
            st.error(f"Query failed: {e}")
            results = []

        st.write(f"Found **{len(results)}** result(s).")
        if results:
            st.session_state.results = results
            st.caption("Loaded into session — visit **Reports** to download PDFs.")
            render_results(results)
