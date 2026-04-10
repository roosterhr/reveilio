"""JobDescription input class.

A :class:`JobDescription` holds the raw text of a JD plus a lazily-computed
structured parse (produced by the LLM). Users can create multiple
independent ``JobDescription`` instances (one per role) and reuse each
against different resumes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reveilio.llm.dynamic import json_completion
from reveilio.parsing.text_extract import extract_text

_JD_SYSTEM_PROMPT = """You are an expert HR job description parser.
Extract structured information including:
- position_title, company, location, work_mode
- required_skills (list of core must-have skills)
- preferred_skills (nice-to-have skills)
- soft_skills (communication, etc.)
- required_experience (number of years)
- preferred_experience (number of years)
- education_requirements (list of degrees)
- certifications (list of required/preferred certs)
- tools_and_technologies, programming_languages, frameworks, databases, cloud_platforms, methodologies
- responsibilities (list)
Return ONLY valid JSON."""


class JobDescription:
    """A job description, sourced from free text, a file path, or raw bytes."""

    def __init__(self, text: str, *, source: str | None = None):
        if not text or not text.strip():
            raise ValueError("JobDescription text is empty.")
        self.text: str = text
        self.source: str | None = source
        self._parsed: dict[str, Any] | None = None

    # ---- constructors ----

    @classmethod
    def from_text(cls, text: str) -> JobDescription:
        """Create from free text (e.g. pasted from an email or form)."""
        return cls(text, source="text")

    @classmethod
    def from_file(cls, path: str | Path) -> JobDescription:
        """Create from a ``.pdf``, ``.docx``, ``.doc``, or ``.txt`` file."""
        path = Path(path)
        return cls(extract_text(path), source=str(path))

    @classmethod
    def from_bytes(cls, data: bytes, filename: str) -> JobDescription:
        """Create from in-memory file bytes. ``filename`` must include the extension."""
        return cls(extract_text(data, filename=filename), source=filename)

    # ---- lazy structured parse ----

    @property
    def parsed(self) -> dict[str, Any]:
        """Structured JD dict, computed lazily on first access."""
        if self._parsed is None:
            self._parsed = self._parse_with_llm(self.text)
        return self._parsed

    @staticmethod
    def _parse_with_llm(text: str) -> dict[str, Any]:
        user_prompt = f"Extract JD data from this text:\n\n{text[:8000]}"
        try:
            raw = json_completion(
                system_prompt=_JD_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.1,
                response_json=True,
            )
            return json.loads(raw)
        except Exception:
            return {"position_title": "N/A", "required_skills": [], "required_experience": 0}

    def __repr__(self) -> str:  # pragma: no cover - trivial
        title = (self._parsed or {}).get("position_title") if self._parsed else None
        tag = f" title={title!r}" if title else ""
        return f"<JobDescription source={self.source!r}{tag}>"
