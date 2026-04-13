"""Plain-text extraction from PDF, DOCX, DOC, and TXT files.

Supports the extensions: ``.pdf``, ``.docx``, ``.doc``, ``.txt``.
Free text (``str``) is handled at a higher level. These helpers operate
on file bytes.
"""

from __future__ import annotations

import contextlib
import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import docx
import PyPDF2

SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".doc", ".txt")


def extract_text(source: bytes | str | Path, filename: str | None = None) -> str:
    """Extract plain text from a file path or raw bytes.

    Parameters
    ----------
    source:
        Either a path (``str``/``Path``) to a file on disk, or the raw
        ``bytes`` of the file's contents.
    filename:
        Required when ``source`` is bytes, so the extension can be
        detected. Ignored otherwise.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        data = path.read_bytes()
        name = path.name
    else:
        if not filename:
            raise ValueError("filename is required when passing raw bytes to extract_text().")
        data = source
        name = filename

    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext == "pdf":
        return _from_pdf(data)
    if ext == "docx":
        return _from_docx(data)
    if ext == "doc":
        return _from_doc(data)
    if ext == "txt":
        return data.decode("utf-8", errors="replace")

    raise ValueError(
        f"Unsupported file extension {ext!r}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def _from_pdf(data: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _from_docx(data: bytes) -> str:
    d = docx.Document(io.BytesIO(data))
    return "\n".join(p.text for p in d.paragraphs)


def _from_doc(data: bytes) -> str:
    # Some tools save OOXML/RTF with a .doc extension; handle those first.
    head = data[:64].lstrip()
    if head.startswith(b"{\\rtf"):
        # Best-effort RTF → text without a hard dep: strip control words.
        return _strip_rtf(data.decode("latin-1", errors="ignore"))
    if len(data) >= 2 and data[:2] == b"PK":
        try:
            return _from_docx(data)
        except Exception:
            pass

    # Prefer antiword if available
    text = _antiword(data)
    if text and text.strip():
        return text

    # UTF-16LE runs are common in Word binary streams
    text = _utf16le_runs(data)
    if text and len(text.strip()) >= 12:
        return text

    # Last resort: printable ASCII runs
    raw = data.decode("latin-1", errors="ignore")
    return "\n".join(re.findall(r"[ -~\t\n\r]{4,}", raw))


def _antiword(data: bytes) -> str:
    antiword = shutil.which("antiword")
    if not antiword:
        return ""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".doc", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        proc = subprocess.run(
            [antiword, tmp_path], capture_output=True, text=True, timeout=60, check=False
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    except Exception:
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
    return ""


def _utf16le_runs(data: bytes) -> str:
    parts: list[str] = []
    for m in re.finditer(rb"(?:[\x20-\x7E\x09\x0a\x0d]\x00){6,}", data):
        try:
            chunk = m.group(0).decode("utf-16le", errors="ignore").strip()
            if len(chunk) >= 4 and not chunk.isdigit():
                parts.append(chunk)
        except Exception:
            continue
    return "\n".join(parts)


def _strip_rtf(rtf: str) -> str:
    # Minimal RTF stripper: remove control words/groups/braces.
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", rtf)
    text = re.sub(r"[{}]", "", text)
    return text
