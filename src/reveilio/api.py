"""High-level synchronous entry points.

All functions here accept either file paths, raw bytes, free text, or
pre-built :class:`JobDescription` / :class:`Resume` objects, and return
plain dicts (or :class:`AnalysisResult` models).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Union

from reveilio.models import AnalysisResult
from reveilio.parsing.job_description import JobDescription
from reveilio.parsing.resume import Resume
from reveilio.parsing.text_extract import SUPPORTED_EXTENSIONS
from reveilio.reports.pdf import generate_batch_report, generate_candidate_report
from reveilio.scoring.scorer import calculate_match

ResumeLike = Union[Resume, str, Path, bytes]
JDLike = Union[JobDescription, str, Path]


def _coerce_jd(jd: JDLike) -> JobDescription:
    if isinstance(jd, JobDescription):
        return jd
    if isinstance(jd, (str, Path)):
        p = Path(str(jd))
        # Treat as a file path only if it exists AND has a supported extension.
        if p.exists() and p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            return JobDescription.from_file(p)
        return JobDescription.from_text(str(jd))
    raise TypeError(f"Unsupported JD type: {type(jd).__name__}")


def _coerce_resume(resume: ResumeLike) -> Resume:
    if isinstance(resume, Resume):
        return resume
    if isinstance(resume, bytes):
        raise TypeError("Resume bytes require a filename. Use Resume.from_bytes(data, filename).")
    if isinstance(resume, (str, Path)):
        p = Path(str(resume))
        if p.exists() and p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            return Resume.from_file(p)
        # Treat as free text (e.g. already-extracted resume text)
        return Resume.from_text(str(resume))
    raise TypeError(f"Unsupported resume type: {type(resume).__name__}")


def score(resume: ResumeLike, jd: JDLike) -> AnalysisResult:
    """Low-level scoring: returns an :class:`AnalysisResult` for one resume."""
    r = _coerce_resume(resume)
    j = _coerce_jd(jd)
    data = calculate_match(r.text, j.parsed, filename=r.filename)
    return AnalysisResult.model_validate(data)


def analyze_resume(resume: ResumeLike, jd: JDLike) -> AnalysisResult:
    """Analyze a single resume against a job description.

    ``resume`` can be a file path, a :class:`Resume`, or a free-text string.
    ``jd`` can be a file path, a :class:`JobDescription`, or a free-text string.
    """
    return score(resume, jd)


def analyze_folder(
    folder: str | Path,
    jd: JDLike,
    *,
    extensions: tuple[str, ...] = SUPPORTED_EXTENSIONS,
    max_workers: int = 4,
    recursive: bool = False,
) -> list[AnalysisResult]:
    """Analyze every supported resume file in a folder against a JD.

    Results are returned sorted by ``overall_score`` descending and tagged
    with a 1-based ``rank`` field.
    """
    folder = Path(folder)
    if not folder.exists() or not folder.is_dir():
        raise ValueError(f"Not a directory: {folder}")

    j = _coerce_jd(jd)
    # Force JD parse once up front so every worker reuses the cached result.
    _ = j.parsed

    iterator = folder.rglob("*") if recursive else folder.iterdir()
    files = [p for p in iterator if p.is_file() and p.suffix.lower() in extensions]

    results: list[AnalysisResult] = []
    if not files:
        return results

    def _work(path: Path) -> AnalysisResult:
        return score(Resume.from_file(path), j)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_work, p): p for p in files}
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: float(r.overall_score or 0), reverse=True)
    for i, r in enumerate(results, start=1):
        r.rank = i
    return results


# ---- PDF report helpers ----


def _as_dict(result: AnalysisResult | dict[str, Any]) -> dict[str, Any]:
    if isinstance(result, AnalysisResult):
        return result.model_dump()
    return result


def save_report_pdf(
    result: AnalysisResult | dict[str, Any],
    path: str | Path,
) -> Path:
    """Write a single-candidate analysis report to ``path`` as a PDF."""
    buf = generate_candidate_report(_as_dict(result))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(buf.getvalue())
    return out


def save_batch_report_pdf(
    results: list[AnalysisResult | dict[str, Any]],
    path: str | Path,
) -> Path:
    """Write a batch ranking summary PDF to ``path``."""
    buf = generate_batch_report([_as_dict(r) for r in results])
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(buf.getvalue())
    return out
