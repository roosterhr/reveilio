"""Resume input class.

A :class:`Resume` simply wraps the extracted plain text of a candidate's
resume. Structured parsing + scoring happens in :mod:`reveilio.scoring`,
which combines both in a single LLM call.
"""

from __future__ import annotations

from pathlib import Path

from reveilio.parsing.text_extract import extract_text


class Resume:
    def __init__(self, text: str, *, filename: str | None = None):
        if not text or not text.strip():
            raise ValueError("Resume text is empty.")
        self.text: str = text
        self.filename: str = filename or "resume"

    # ---- constructors ----

    @classmethod
    def from_text(cls, text: str, *, filename: str = "resume.txt") -> Resume:
        return cls(text, filename=filename)

    @classmethod
    def from_file(cls, path: str | Path) -> Resume:
        p = Path(path)
        return cls(extract_text(p), filename=p.name)

    @classmethod
    def from_bytes(cls, data: bytes, filename: str) -> Resume:
        return cls(extract_text(data, filename=filename), filename=filename)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resume filename={self.filename!r} length={len(self.text)}>"
