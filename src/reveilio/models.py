"""Pydantic models for reveilio analysis results."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ExperienceItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    title: str | None = None
    company: str | None = None
    duration: str | None = None
    description: str | None = None
    location: str | None = None


class EducationItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    degree: str | None = None
    institution: str | None = None
    year: str | None = None
    location: str | None = None


class ResumeData(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    skills: list[str] = []
    experience: list[ExperienceItem] = []
    education: list[EducationItem] = []
    certifications: list[str] = []
    total_experience: float = 0
    top_keywords: list[str] = []
    career_gaps: list[Any] = []
    filename: str | None = None


class DetailedScores(BaseModel):
    model_config = ConfigDict(extra="allow")


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    overall_score: float = 0
    confidence_level: str = "Medium"
    recommendation: str = "Needs Review"
    detailed_scores: dict[str, Any] = {}
    jd_analysis: dict[str, Any] = {}
    ai_summary: str = ""
    strengths: list[str] = []
    weaknesses: list[str] = []
    career_flags: list[str] = []
    match_breakdown: Any = {}
    reasoning: Any | None = None
    experience_analysis: Any | None = None
    kpis: list[Any] = []
    relevancy_metrics: list[Any] = []
    suggested_roles: list[Any] = []
    suggested_questions: list[str] = []
    candidate_data: ResumeData | None = None
    rank: int | None = None
