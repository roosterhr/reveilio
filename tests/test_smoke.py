"""Smoke tests. No real LLM calls; the LLM layer is monkey-patched."""

from __future__ import annotations

import json

import pytest

import reveilio
from reveilio.parsing.job_description import JobDescription
from reveilio.parsing.resume import Resume


@pytest.fixture(autouse=True)
def _reset_config():
    reveilio.configure(provider="gemini", api_key="test-key")
    yield


@pytest.fixture
def fake_llm(monkeypatch):
    """Patch json_completion everywhere it's imported."""

    def _fake(system_prompt, user_prompt, **_kwargs):
        if "job description parser" in system_prompt.lower():
            return json.dumps(
                {
                    "position_title": "Senior Python Engineer",
                    "required_skills": ["Python"],
                    "required_experience": 5,
                }
            )
        # scoring prompt
        return json.dumps(
            {
                "candidate_data": {
                    "name": "Alice Example",
                    "email": "alice@example.com",
                    "skills": ["Python", "FastAPI"],
                    "experience": [],
                    "education": [],
                    "certifications": [],
                    "total_experience": 6,
                    "top_keywords": ["Python"],
                    "career_gaps": [],
                },
                "overall_score": 82,
                "confidence_level": "High",
                "recommendation": "Shortlist",
                "detailed_scores": {
                    "skills": {"score": 90, "reasoning": "strong match"},
                },
                "strengths": ["Deep Python"],
                "weaknesses": [],
                "career_flags": [],
                "ai_summary": "Good fit.",
                "match_breakdown": {},
                "reasoning": ["x"],
                "experience_analysis": ["y"],
                "kpis": [],
                "relevancy_metrics": [],
                "suggested_roles": [],
                "suggested_questions": ["Tell me about FastAPI at scale?"],
            }
        )

    import reveilio.llm.dynamic as dyn
    import reveilio.parsing.job_description as jdmod
    import reveilio.scoring.scorer as sc

    monkeypatch.setattr(dyn, "json_completion", _fake)
    monkeypatch.setattr(jdmod, "json_completion", _fake)
    monkeypatch.setattr(sc, "json_completion", _fake)


def test_configure_and_get_config():
    cfg = reveilio.get_config()
    assert cfg.provider == "gemini"
    assert cfg.api_key == "test-key"
    assert "skills" in cfg.weights


def test_job_description_from_text_lazy_parse(fake_llm):
    jd = JobDescription.from_text("We need a Senior Python Engineer with 5+ years.")
    assert jd.parsed["position_title"] == "Senior Python Engineer"


def test_analyze_resume_with_free_text(fake_llm):
    jd = JobDescription.from_text("Senior Python role")
    resume = Resume.from_text("Alice with 6 years Python, FastAPI, AWS.", filename="alice.txt")
    result = reveilio.analyze_resume(resume, jd)
    assert result.overall_score == 82
    assert result.recommendation == "Shortlist"
    assert result.candidate_data.name == "Alice Example"
    # suggested_questions preserved for Shortlist
    assert result.suggested_questions


def test_analyze_folder(tmp_path, fake_llm):
    (tmp_path / "a.txt").write_text("Alice Python FastAPI", encoding="utf-8")
    (tmp_path / "b.txt").write_text("Bob Java Spring", encoding="utf-8")

    jd = JobDescription.from_text("Senior Python role")
    results = reveilio.analyze_folder(tmp_path, jd)
    assert len(results) == 2
    assert results[0].rank == 1
    assert results[1].rank == 2


def test_save_report_pdf(tmp_path, fake_llm):
    jd = JobDescription.from_text("Senior Python role")
    result = reveilio.analyze_resume(Resume.from_text("Alice Python", filename="alice.txt"), jd)
    out = reveilio.save_report_pdf(result, tmp_path / "report.pdf")
    assert out.exists() and out.stat().st_size > 500
    assert out.read_bytes().startswith(b"%PDF")
