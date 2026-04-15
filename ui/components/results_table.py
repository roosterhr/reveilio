"""Shared rendering for analysis results.

Mirrors the sections produced by ``reveilio.reports.pdf.generate_candidate_report``
so the on-screen view and the downloadable PDF carry the same information.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import streamlit as st

from reveilio.models import AnalysisResult


def results_to_dataframe(results: Iterable[AnalysisResult]) -> pd.DataFrame:
    """Flatten a list of AnalysisResults into a summary dataframe."""
    rows = []
    for r in results:
        c = r.candidate_data
        rows.append(
            {
                "Rank": r.rank,
                "Candidate": getattr(c, "name", None) or "—",
                "Score": r.overall_score,
                "Recommendation": r.recommendation,
                "Confidence": r.confidence_level,
                "Experience (yrs)": getattr(c, "total_experience", None),
                "File": getattr(c, "filename", None) or "—",
            }
        )
    return pd.DataFrame(rows)


def render_results(results: list[AnalysisResult]) -> None:
    """Render a ranked dataframe plus an expandable per-candidate view."""
    if not results:
        st.info("No results yet. Run an analysis from the Analyze page.")
        return

    df = results_to_dataframe(results)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Candidate details")
    for r in results:
        name = getattr(r.candidate_data, "name", None) or "Unknown candidate"
        with st.expander(f"{name} — {r.overall_score}% ({r.recommendation})"):
            _render_single(r)


def _render_single(r: AnalysisResult) -> None:
    _render_header(r)
    _render_summary(r)
    _render_suggested_roles(r)
    _render_detailed_scores(r)
    _render_key_insights(r)
    _render_career_flags(r)
    _render_experience_analysis(r)
    _render_kpis(r)
    _render_reasoning(r)
    _render_relevancy_metrics(r)
    _render_suggested_questions(r)
    _render_candidate_profile(r)


def _render_header(r: AnalysisResult) -> None:
    c = r.candidate_data
    if not c:
        return
    cols = st.columns(4)
    cols[0].metric("Score", f"{r.overall_score}%")
    cols[1].metric("Recommendation", r.recommendation or "—")
    cols[2].metric("Confidence", r.confidence_level or "—")
    cols[3].metric("Experience", f"{getattr(c, 'total_experience', 0) or 0} yrs")

    meta_cols = st.columns(3)
    meta_cols[0].markdown(f"**Email:** {getattr(c, 'email', None) or '—'}")
    meta_cols[1].markdown(f"**Phone:** {getattr(c, 'phone', None) or '—'}")
    meta_cols[2].markdown(f"**LinkedIn:** {getattr(c, 'linkedin', None) or '—'}")


def _render_summary(r: AnalysisResult) -> None:
    if not r.ai_summary:
        return
    st.markdown("### Executive Summary")
    st.write(r.ai_summary)


def _render_suggested_roles(r: AnalysisResult) -> None:
    roles = r.suggested_roles or []
    if not roles:
        return
    st.markdown("### AI Fit Suggestions — Alternative Roles")
    for role in roles:
        if isinstance(role, dict):
            label = role.get("role") or role.get("title") or "Unknown"
            reason = role.get("reasoning") or role.get("reason") or ""
            st.markdown(f"- **{label}** — {reason}" if reason else f"- **{label}**")
        else:
            st.markdown(f"- {role}")


def _render_detailed_scores(r: AnalysisResult) -> None:
    scores = r.detailed_scores or {}
    if not scores:
        return
    st.markdown("### Detailed Metrics")
    rows = []
    for cat, details in scores.items():
        cat_name = cat.replace("_", " ").title()
        if isinstance(details, dict):
            score = details.get("score", 0)
            reasoning = details.get("reasoning", "—")
        else:
            score = details
            reasoning = "—"
        rows.append({"Category": cat_name, "Score": f"{score}%", "Reasoning": reasoning})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_key_insights(r: AnalysisResult) -> None:
    if not (r.strengths or r.weaknesses):
        return
    st.markdown("### Key Insights")
    col_s, col_w = st.columns(2)
    with col_s:
        st.markdown("**Strengths**")
        if r.strengths:
            for s in r.strengths:
                st.markdown(f"- {s}")
        else:
            st.caption("—")
    with col_w:
        st.markdown("**Gaps / Weaknesses**")
        if r.weaknesses:
            for w in r.weaknesses:
                st.markdown(f"- {w}")
        else:
            st.caption("—")


def _render_career_flags(r: AnalysisResult) -> None:
    flags = r.career_flags or []
    if not flags:
        return
    st.markdown("### Career Red Flags")
    for f in flags:
        st.markdown(f"- {f}")


def _render_experience_analysis(r: AnalysisResult) -> None:
    exp = r.experience_analysis
    if not exp:
        return
    st.markdown("### Experience Relevance Analysis")
    if isinstance(exp, list):
        for p in exp:
            st.markdown(f"- {p}")
    else:
        st.write(str(exp))


def _render_kpis(r: AnalysisResult) -> None:
    kpis = r.kpis or []
    if not kpis:
        return
    st.markdown("### Key Performance Indicators (KPIs)")
    for k in kpis:
        st.markdown(f"- {k}")


def _render_reasoning(r: AnalysisResult) -> None:
    reasoning = r.reasoning
    if not reasoning:
        return
    st.markdown("### AI Matching Reasoning")
    if isinstance(reasoning, list):
        for p in reasoning:
            st.markdown(f"- {p}")
    else:
        st.write(str(reasoning))


def _render_relevancy_metrics(r: AnalysisResult) -> None:
    metrics = r.relevancy_metrics or []
    if not metrics:
        return
    st.markdown("### Relevancy Metrics & Measurements")
    rows = []
    for m in metrics:
        if isinstance(m, dict):
            rows.append(
                {
                    "Metric": m.get("metric", "—"),
                    "Value": m.get("value", "—"),
                    "Relevancy": str(m.get("relevancy", "—")).upper(),
                }
            )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_suggested_questions(r: AnalysisResult) -> None:
    questions = r.suggested_questions or []
    if not questions:
        return
    st.markdown("### Suggested Interview Questions")
    for q in questions:
        st.markdown(f"- {q}")


def _render_candidate_profile(r: AnalysisResult) -> None:
    c = r.candidate_data
    if not c:
        return
    skills = getattr(c, "skills", None) or []
    certs = getattr(c, "certifications", None) or []
    experience = getattr(c, "experience", None) or []
    education = getattr(c, "education", None) or []

    if not (skills or certs or experience or education):
        return

    st.markdown("### Candidate Profile")
    if skills:
        st.markdown(f"**Skills:** {', '.join(skills)}")
    if certs:
        st.markdown(f"**Certifications:** {', '.join(certs)}")
    if experience:
        st.markdown("**Experience**")
        for item in experience:
            title = getattr(item, "title", None) or "—"
            company = getattr(item, "company", None) or "—"
            duration = getattr(item, "duration", None) or ""
            st.markdown(f"- {title} @ {company} ({duration})")
    if education:
        st.markdown("**Education**")
        for item in education:
            degree = getattr(item, "degree", None) or "—"
            inst = getattr(item, "institution", None) or "—"
            year = getattr(item, "year", None) or ""
            st.markdown(f"- {degree}, {inst} ({year})")
