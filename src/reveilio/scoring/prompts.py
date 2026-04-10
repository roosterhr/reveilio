"""System/user prompt builders for the combined extract-and-score call."""
from __future__ import annotations

import json
from typing import Any


def build_system_prompt(weights: dict[str, float]) -> str:
    weights_desc = ", ".join(f"{k}: {int(v * 100)}%" for k, v in weights.items())
    detailed_scores_keys = ", ".join(
        f'"{k}": {{ "score": 0, "reasoning": "Brief explanation" }}' for k in weights
    )
    return f"""You are an expert talent acquisition AI.
Perform a deep-dive analysis of the Candidate Resume and compare it against the Job Description.

### PHASE 1: Structured Extraction
Extract structured data from the resume with extreme detail (Experience items, Skills, Education, Certifications, etc.).

### PHASE 2: Match Analysis
Compare the extracted candidate data against the JD using weighted criteria ({weights_desc}).

### OUTPUT FORMAT
Return ONLY valid JSON with this EXACT structure:
{{
    "candidate_data": {{
        "name": "Full Name",
        "email": "Email Address",
        "phone": "Phone Number",
        "linkedin": "LinkedIn URL",
        "skills": ["Skill 1", "Skill 2"],
        "experience": [
            {{"title": "Job Title", "company": "Company Name", "duration": "Dates/Duration", "description": "Responsibilities and achievements", "location": "City, Country"}}
        ],
        "education": [
            {{"degree": "Degree/Major", "institution": "School Name", "year": "Graduation Year", "location": "City, Country"}}
        ],
        "certifications": ["Cert 1"],
        "total_experience": 0,
        "top_keywords": ["keyword1", "keyword2"],
        "career_gaps": ["Description of gaps"]
    }},
    "overall_score": 0-100,
    "confidence_level": "High/Medium/Low",
    "recommendation": "Shortlist/Needs Review/Not Suitable",
    "detailed_scores": {{ {detailed_scores_keys} }},
    "strengths": ["match point 1", "match point 2"],
    "weaknesses": ["gap 1", "gap 2"],
    "career_flags": ["Flag: Detail"],
    "ai_summary": "Objective critique (120 words or less)",
    "match_breakdown": {{ "internal details": "..." }},
    "reasoning": ["logic 1", "logic 2"],
    "experience_analysis": ["deep dive 1", "deep dive 2"],
    "kpis": ["KPI 1", "KPI 2"],
    "relevancy_metrics": [
        {{"metric": "Name", "value": "Value", "relevancy": "high/medium/low", "reasoning": "mathematical breakdown", "criteria": {{"High": "...", "Medium": "...", "Low": "..."}}}}
    ],
    "suggested_roles": [{{"role": "Title", "match_score": 0-100}}],
    "suggested_questions": ["If and only if recommendation is Shortlist: 3-5 role-aligned live interview questions from JD + resume; otherwise []"]
}}

MANDATORY:
- If recommendation is **Needs Review** or **Not Suitable**, set "suggested_questions" to []. Only populate when recommendation is **Shortlist**.
- For each entry in "detailed_scores", provide both a "score" (0-100) and a "reasoning" (short text explaining the score).
- Include "Average Tenure per Company" in relevancy_metrics.
- Wrap important keywords in **double asterisks**.
"""


def build_user_prompt(resume_text: str, jd_data: dict[str, Any]) -> str:
    return f"""
RESUME RAW TEXT:
---
{resume_text[:8000]}
---

JOB DESCRIPTION DATA (STRUCTURED):
---
{json.dumps(jd_data, indent=2)}
---

Perform extraction and match analysis.
"""
