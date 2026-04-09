"""Unit tests for knowledge_base.extractor"""

import pytest
from pathlib import Path
import tempfile

from knowledge_base.extractor import detect_format, extract_text


def test_detect_format_markdown():
    assert detect_format("article.md") == "markdown"
    assert detect_format("ARTICLE.MD") == "markdown"
    assert detect_format("post.markdown") == "markdown"


def test_detect_format_txt():
    assert detect_format("notes.txt") == "txt"


def test_detect_format_html():
    assert detect_format("page.html") == "html"
    assert detect_format("page.htm") == "html"


def test_detect_format_pdf():
    assert detect_format("doc.pdf") == "pdf"


def test_detect_format_docx():
    assert detect_format("doc.docx") == "docx"


def test_detect_format_unknown_defaults_to_txt():
    assert detect_format("file.xyz") == "txt"


def test_extract_text_markdown():
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# Title\n\nSome **bold** content.\n")
        path = Path(f.name)

    result = extract_text(path, "markdown")
    assert "Title" in result
    assert "bold" in result
    path.unlink()


def test_extract_text_txt():
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write("Plain text content here.")
        path = Path(f.name)

    result = extract_text(path, "txt")
    assert "Plain text content here." in result
    path.unlink()


def test_extract_text_html_strips_scripts():
    html = """<html><head><script>alert('xss')</script></head>
    <body><h1>Title</h1><p>Content</p></body></html>"""
    with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as f:
        f.write(html)
        path = Path(f.name)

    result = extract_text(path, "html")
    assert "Title" in result
    assert "Content" in result
    assert "alert" not in result
    path.unlink()
