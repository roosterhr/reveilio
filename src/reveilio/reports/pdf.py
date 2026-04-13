"""PDF report generation for analysis results.

Ported from ``backend/app/services/pdf_service.py``. Returns an
``io.BytesIO`` buffer that callers can write to disk or stream.
"""

from __future__ import annotations

import io
import re
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CustomTitle",
            parent=base["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=24,
            alignment=1,
        ),
        "heading": ParagraphStyle(
            "CustomHeading",
            parent=base["Heading2"],
            fontSize=16,
            textColor=colors.HexColor("#334155"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "sub_heading": ParagraphStyle(
            "CustomSubHeading",
            parent=base["Heading3"],
            fontSize=12,
            textColor=colors.HexColor("#64748b"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "CustomBody",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#475569"),
            leading=14,
        ),
    }


def _md(text: str, color: str | None = None) -> str:
    if not text:
        return ""
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    if color:
        return re.sub(r"\*\*(.*?)\*\*", rf'<b><font color="{color}">\1</font></b>', text)
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)


def generate_candidate_report(result: dict[str, Any]) -> io.BytesIO:
    """Generate a professional single-candidate PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18
    )
    s = _styles()
    el: list[Any] = []

    candidate = result.get("candidate_data") or {}
    name = candidate.get("name", "Candidate")
    overall = result.get("overall_score", 0)
    recommendation = result.get("recommendation", "N/A")
    jd = result.get("jd_analysis") or {}
    position = jd.get("position_title", "N/A")

    el.append(Paragraph("Candidate Evaluation Report", s["title"]))
    el.append(Paragraph(f"Role: {position}", s["sub_heading"]))
    el.append(Paragraph(f"Name: {name}", s["heading"]))
    el.append(
        Paragraph(f"Score: {int(overall)}% | Recommendation: {recommendation}", s["sub_heading"])
    )
    el.append(Spacer(1, 0.2 * inch))

    el.append(Paragraph("Executive Summary", s["heading"]))
    el.append(
        Paragraph(_md(result.get("ai_summary", "No summary available."), "#000000"), s["body"])
    )
    el.append(Spacer(1, 0.2 * inch))

    suggested_roles = result.get("suggested_roles") or []
    if suggested_roles:
        el.append(Paragraph("AI Fit Suggestions (Alternative Roles)", s["sub_heading"]))
        roles = []
        for role in suggested_roles:
            if isinstance(role, dict):
                roles.append(role.get("role", "Unknown"))
            else:
                roles.append(str(role))
        el.append(Paragraph("Possible suitable positions: " + ", ".join(roles), s["body"]))
        el.append(Spacer(1, 0.2 * inch))

    el.append(Paragraph("Detailed Metrics", s["heading"]))
    scores = result.get("detailed_scores") or {}
    data: list[list[Any]] = [["Category", "Score", "Reasoning"]]
    for cat, details in scores.items():
        cat_name = cat.replace("_", " ").capitalize()
        if isinstance(details, dict):
            score_val = details.get("score", 0)
            reasoning = details.get("reasoning", "N/A")
        else:
            score_val, reasoning = details, "N/A"
        rs = str(reasoning)
        if len(rs) > 150:
            rs = rs[:150] + "..."
        data.append([cat_name, f"{score_val}%", Paragraph(_md(rs), s["body"])])

    t = Table(data, colWidths=[1.5 * inch, 0.8 * inch, 4.2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )
    el.append(t)
    el.append(Spacer(1, 0.2 * inch))

    el.append(Paragraph("Key Insights", s["heading"]))
    strengths = result.get("strengths") or []
    weaknesses = result.get("weaknesses") or []
    s_text = "".join(f"• {_md(x, '#10b981')}<br/>" for x in strengths)
    w_text = "".join(f"• {_md(x, '#ef4444')}<br/>" for x in weaknesses)
    insight_table = Table(
        [
            [
                Paragraph("<b>Strengths</b>", s["sub_heading"]),
                Paragraph("<b>Gaps/Weaknesses</b>", s["sub_heading"]),
            ],
            [Paragraph(s_text, s["body"]), Paragraph(w_text, s["body"])],
        ],
        colWidths=[2.5 * inch, 2.5 * inch],
    )
    insight_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]
        )
    )
    el.append(insight_table)
    el.append(Spacer(1, 0.2 * inch))

    flags = result.get("career_flags") or []
    if flags:
        el.append(Paragraph("Career Red Flags", s["heading"]))
        for flag in flags:
            el.append(Paragraph(f"• {flag}", s["body"]))
        el.append(Spacer(1, 0.2 * inch))

    el.append(Paragraph("Experience Relevance Analysis", s["heading"]))
    exp = result.get("experience_analysis") or "N/A"
    if isinstance(exp, list):
        for point in exp:
            el.append(Paragraph(f"• {_md(str(point))}", s["body"]))
    else:
        el.append(Paragraph(_md(str(exp)), s["body"]))
    el.append(Spacer(1, 0.2 * inch))

    kpis = result.get("kpis") or []
    if kpis:
        el.append(Paragraph("Key Performance Indicators (KPIs)", s["heading"]))
        for kpi in kpis:
            el.append(Paragraph(f"• {_md(str(kpi), '#b45309')}", s["body"]))
        el.append(Spacer(1, 0.2 * inch))

    el.append(Paragraph("AI Matching Reasoning", s["heading"]))
    reasoning = result.get("reasoning") or "No reasoning available."
    if isinstance(reasoning, list):
        for point in reasoning:
            el.append(Paragraph(f"• {_md(str(point))}", s["body"]))
    else:
        el.append(Paragraph(_md(str(reasoning)), s["body"]))
    el.append(Spacer(1, 0.2 * inch))

    rel_metrics = result.get("relevancy_metrics") or []
    if rel_metrics:
        el.append(Paragraph("Relevancy Metrics & Measurements", s["heading"]))
        rel_data: list[list[Any]] = [["Metric", "Value", "Relevancy"]]
        for m in rel_metrics:
            rel_data.append(
                [
                    m.get("metric", "N/A"),
                    m.get("value", "N/A"),
                    str(m.get("relevancy", "N/A")).upper(),
                ]
            )
        rt = Table(rel_data, colWidths=[2.5 * inch, 1.5 * inch, 1.0 * inch])
        rt.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]
            )
        )
        el.append(rt)

    doc.build(el)
    buffer.seek(0)
    return buffer


def generate_batch_report(results: list[dict[str, Any]]) -> io.BytesIO:
    """Generate a ranking summary PDF for a batch of candidates."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    s = _styles()
    el: list[Any] = []

    el.append(Paragraph("Batch Analysis Ranking Summary", s["title"]))
    jd = results[0].get("jd_analysis", {}) if results else {}
    position = jd.get("position_title", "N/A")
    el.append(Paragraph(f"Role: {position}", s["sub_heading"]))
    el.append(Spacer(1, 0.3 * inch))

    data: list[list[Any]] = [["Rank", "Candidate Name", "Score", "Recommendation", "Experience"]]
    for res in results:
        candidate = res.get("candidate_data") or {}
        data.append(
            [
                res.get("rank", "-"),
                candidate.get("name", "N/A"),
                f"{int(res.get('overall_score', 0))}%",
                res.get("recommendation", "N/A"),
                f"{candidate.get('total_experience', 0)} Years",
            ]
        )

    t = Table(data, colWidths=[0.5 * inch, 2 * inch, 0.7 * inch, 1.3 * inch, 1.5 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (1, 1),
                    (-1, -1),
                    [colors.whitesmoke, colors.HexColor("#f1f5f9")],
                ),
            ]
        )
    )
    el.append(t)

    doc.build(el)
    buffer.seek(0)
    return buffer
