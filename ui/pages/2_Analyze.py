"""Analyze page: upload a JD + resumes and produce ranked results."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

import reveilio  # noqa: E402
from branding import init_page  # noqa: E402
from components.results_table import render_results  # noqa: E402

init_page(title="Analyze | reveilio", icon="📊")
st.title("Analyze")

if not st.session_state.get("llm_configured"):
    st.warning("Configure an LLM provider first (sidebar → Configure).")
    st.stop()


def _save_upload(uploaded, suffix: str) -> Path:
    """Persist an uploaded file to a tempfile and return its path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        return Path(tmp.name)


st.subheader("Step 1 — Job description")
jd_mode = st.radio("JD source", ["Upload file", "Paste text"], horizontal=True, key="jd_mode")

if jd_mode == "Upload file":
    jd_file = st.file_uploader(
        "Job description file",
        type=["pdf", "docx", "doc", "txt"],
        key="jd_upload",
    )
    jd_text = None
else:
    jd_file = None
    jd_text = st.text_area("Paste the job description", height=200, key="jd_text")

st.divider()

st.subheader("Step 2 — Resumes")
resume_mode = st.radio(
    "Resume source",
    ["Single file", "Bulk upload (multiple files)", "Folder (zip archive)"],
    horizontal=True,
    key="resume_mode",
)

resume_upload = None
bulk_uploads = None
zip_upload = None

if resume_mode == "Single file":
    resume_upload = st.file_uploader(
        "Resume file",
        type=["pdf", "docx", "doc", "txt"],
        key="resume_single",
    )
elif resume_mode == "Bulk upload (multiple files)":
    bulk_uploads = st.file_uploader(
        "Resume files (pick multiple)",
        type=["pdf", "docx", "doc", "txt"],
        accept_multiple_files=True,
        key="resume_bulk",
    )
    if bulk_uploads:
        st.caption(f"{len(bulk_uploads)} file(s) selected.")
else:
    zip_upload = st.file_uploader(
        "Zip archive of resumes",
        type=["zip"],
        key="resume_zip",
    )

st.divider()

save_to_db = False
job_title = ""
if st.session_state.get("db_connected"):
    save_to_db = st.checkbox("Save results to the connected database", value=False)
    job_title = st.text_input("Job title (stored as metadata)", value="")
else:
    st.caption("Connect a database on the Configure page to enable saving.")

# Input readiness check
jd_ready = (jd_file is not None) or (jd_text and jd_text.strip())
resume_ready = (
    (resume_upload is not None)
    or (zip_upload is not None)
    or (bulk_uploads is not None and len(bulk_uploads) > 0)
)

run = st.button(
    "Run analysis",
    type="primary",
    disabled=not (jd_ready and resume_ready),
)

if run:
    # Build JD
    if jd_file is not None:
        jd_path = _save_upload(jd_file, suffix=Path(jd_file.name).suffix)
        jd = reveilio.JobDescription.from_file(jd_path)
    else:
        jd = reveilio.JobDescription.from_text(jd_text or "")
    st.session_state.jd = jd

    # Score resume(s)
    if resume_mode == "Single file":
        resume_path = _save_upload(resume_upload, suffix=Path(resume_upload.name).suffix)
        with st.spinner("Scoring resume…"):
            result = reveilio.analyze_resume(resume_path, jd)
        result.rank = 1
        results = [result]
    elif resume_mode == "Bulk upload (multiple files)":
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            for uploaded in bulk_uploads:
                safe_name = Path(uploaded.name).name
                (tmp_path / safe_name).write_bytes(uploaded.getbuffer())
            with st.spinner(f"Scoring {len(bulk_uploads)} resume(s)…"):
                results = reveilio.analyze_folder(tmp_path, jd)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            zpath = Path(tmpdir) / "resumes.zip"
            zpath.write_bytes(zip_upload.getbuffer())
            extract_dir = Path(tmpdir) / "extracted"
            extract_dir.mkdir()
            with zipfile.ZipFile(zpath) as zf:
                zf.extractall(extract_dir)
            with st.spinner("Scoring resumes…"):
                results = reveilio.analyze_folder(extract_dir, jd, recursive=True)

    if save_to_db and st.session_state.get("db_connected"):
        try:
            if len(results) == 1:
                reveilio.export_result(results[0], job_title=job_title or None)
            else:
                reveilio.export_results(results, job_title=job_title or None)
            st.success(f"Saved {len(results)} result(s) to the database.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Database save failed: {e}")

    st.session_state.results = results
    st.success(f"Analyzed {len(results)} resume(s).")

if st.session_state.get("results"):
    st.divider()
    render_results(st.session_state.results)
