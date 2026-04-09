"""Text extraction from various file formats (PDF, DOCX, MD, HTML, TXT)."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".md", ".txt", ".html", ".htm", ".pdf", ".docx"}


def detect_format(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".md", ".markdown"):
        return "markdown"
    if ext == ".txt":
        return "txt"
    if ext in (".html", ".htm"):
        return "html"
    if ext == ".pdf":
        return "pdf"
    if ext == ".docx":
        return "docx"
    return "txt"


def extract_text(file_path: Path, fmt: str) -> str:
    """Extract plain/markdown text from a file. Returns the extracted text."""
    if fmt in ("markdown", "txt"):
        return file_path.read_text(encoding="utf-8", errors="replace")

    if fmt == "html":
        return _extract_html(file_path)

    if fmt == "pdf":
        return _extract_pdf(file_path)

    if fmt == "docx":
        return _extract_docx(file_path)

    return file_path.read_text(encoding="utf-8", errors="replace")


def _extract_html(file_path: Path) -> str:
    """Extract text from HTML using BeautifulSoup (already a project dependency)."""
    from bs4 import BeautifulSoup

    html = file_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style tags
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _extract_pdf(file_path: Path) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        logger.error("PyPDF2 not installed. Run: pip install PyPDF2")
        return "(PDF extraction unavailable — install PyPDF2)"

    reader = PdfReader(str(file_path))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(file_path: Path) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        logger.error("python-docx not installed. Run: pip install python-docx")
        return "(DOCX extraction unavailable — install python-docx)"

    doc = Document(str(file_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
