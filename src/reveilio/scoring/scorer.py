"""Combined extract-and-score: one LLM call produces the structured
candidate data plus a weighted match score against the JD.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from reveilio.config import ReveilioConfig, get_config
from reveilio.llm.dynamic import json_completion
from reveilio.scoring.prompts import build_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)


def _is_shortlist(rec: Any) -> bool:
    s = str(rec or "").lower().strip()
    return s.startswith("shortlist")


def calculate_match(
    resume_text: str,
    jd_data: dict[str, Any],
    *,
    filename: str = "resume",
    config: ReveilioConfig | None = None,
) -> dict[str, Any]:
    """Run the combined extraction + scoring LLM call and return a dict.

    The returned dict is suitable for wrapping in
    :class:`reveilio.models.AnalysisResult`.
    """
    cfg = config or get_config()
    weights = cfg.weights

    system_prompt = build_system_prompt(weights)
    user_prompt = build_user_prompt(resume_text, jd_data)

    try:
        ai_text = json_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            response_json=True,
            config=cfg,
        )
        result = json.loads(ai_text)

        if isinstance(result, list) and result:
            result = result[0]
        if not isinstance(result, dict):
            raise ValueError(f"LLM returned unexpected format: {type(result).__name__}")

        c_data = result.get("candidate_data")
        if isinstance(c_data, dict):
            c_data["filename"] = filename
            result["candidate_data"] = c_data

        result.setdefault("overall_score", 0)
        result.setdefault("confidence_level", "Medium")
        result.setdefault("recommendation", "Needs Review")
        result.setdefault("jd_analysis", jd_data)

        ds = result.get("detailed_scores")
        if not isinstance(ds, dict):
            ds = {}
        for key in weights:
            if key not in ds or not isinstance(ds[key], dict):
                ds[key] = {"score": 0, "reasoning": "Not available"}
            else:
                ds[key].setdefault("score", 0)
                ds[key].setdefault("reasoning", "No detailed reasoning provided.")
        result["detailed_scores"] = ds

        if not _is_shortlist(result.get("recommendation")) or not isinstance(result.get("suggested_questions"), list):
            result["suggested_questions"] = []

        return result

    except Exception as e:
        logger.exception("calculate_match failed for %s", filename)
        return {
            "candidate_data": {
                "name": filename,
                "filename": filename,
                "skills": [],
                "experience": [],
                "education": [],
                "total_experience": 0,
            },
            "overall_score": 0,
            "confidence_level": "Low",
            "recommendation": "Needs Review",
            "detailed_scores": {k: {"score": 0, "reasoning": "Error"} for k in weights},
            "jd_analysis": jd_data,
            "ai_summary": f"Error during analysis: {e}",
            "strengths": [],
            "weaknesses": [],
            "career_flags": ["Analysis error occurred"],
            "match_breakdown": {},
            "reasoning": [str(e)],
            "experience_analysis": ["Error analyzing experience."],
            "kpis": [],
            "relevancy_metrics": [],
            "suggested_roles": [],
            "suggested_questions": [],
        }
