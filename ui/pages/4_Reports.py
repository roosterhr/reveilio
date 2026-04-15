"""Reports page: download PDF reports for the results in session."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

import reveilio  # noqa: E402
from branding import init_page  # noqa: E402

init_page(title="Reports | reveilio", icon="📄")
st.title("Reports")

results = st.session_state.get("results") or []
if not results:
    st.info("No results in session. Run an analysis or load some from the Database page.")
    st.stop()

st.caption(f"{len(results)} result(s) available in session.")

st.subheader("Batch report")
if len(results) > 1:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        batch_path = Path(tmp.name)
    reveilio.save_batch_report_pdf(results, batch_path)
    st.download_button(
        "Download batch ranking PDF",
        data=batch_path.read_bytes(),
        file_name="batch_ranking.pdf",
        mime="application/pdf",
    )
else:
    st.caption("Only one result in session — run a folder analysis to enable batch reports.")

st.divider()
st.subheader("Individual reports")

for r in results:
    name = getattr(r.candidate_data, "name", None) or "candidate"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    filename = f"{safe}_report.pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        report_path = Path(tmp.name)
    reveilio.save_report_pdf(r, report_path)

    cols = st.columns([3, 1, 2])
    cols[0].write(f"**{name}** — {r.overall_score}% ({r.recommendation})")
    cols[1].write(f"Rank: {r.rank or '—'}")
    with cols[2]:
        st.download_button(
            "Download PDF",
            data=report_path.read_bytes(),
            file_name=filename,
            mime="application/pdf",
            key=f"dl_{safe}_{r.rank}",
        )
