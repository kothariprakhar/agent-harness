"""Filesystem-based CRUD for Knowledge Base articles."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from shared.models import KnowledgeBaseArticle, StyleProfile, new_id
from knowledge_base.extractor import detect_format, extract_text, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
ARTICLES_DIR = DATA_DIR / "articles"
INDEX_PATH = DATA_DIR / "index.json"


def _load_index() -> list[dict]:
    if not INDEX_PATH.exists():
        return []
    return json.loads(INDEX_PATH.read_text())


def _save_index(entries: list[dict]) -> None:
    INDEX_PATH.write_text(json.dumps(entries, indent=2))


def list_articles(tags: list[str] | None = None) -> list[KnowledgeBaseArticle]:
    """List all articles, optionally filtered by tags."""
    entries = _load_index()
    articles = [KnowledgeBaseArticle.model_validate(e) for e in entries]
    if tags:
        articles = [a for a in articles if set(tags) & set(a.tags)]
    return articles


def get_article(article_id: str) -> Optional[KnowledgeBaseArticle]:
    """Get a single article by ID."""
    for entry in _load_index():
        if entry["id"] == article_id:
            # Load style profile from disk if exists
            article = KnowledgeBaseArticle.model_validate(entry)
            profile_path = ARTICLES_DIR / article_id / "style_profile.json"
            if profile_path.exists() and article.style_profile is None:
                article.style_profile = StyleProfile.model_validate_json(
                    profile_path.read_text()
                )
            return article
    return None


def get_extracted_text(article_id: str) -> str:
    """Read the extracted markdown text for an article."""
    path = ARTICLES_DIR / article_id / "extracted.md"
    if path.exists():
        return path.read_text()
    return ""


def save_article(
    filename: str,
    file_content: bytes,
    title: str = "",
    tags: list[str] | None = None,
) -> KnowledgeBaseArticle:
    """Save an uploaded article: store file, extract text, return metadata."""
    fmt = detect_format(filename)
    article_id = new_id()
    article_dir = ARTICLES_DIR / article_id
    article_dir.mkdir(parents=True, exist_ok=True)

    # Save original file
    ext = Path(filename).suffix or ".txt"
    original_path = article_dir / f"original{ext}"
    original_path.write_bytes(file_content)

    # Extract text
    extracted = extract_text(original_path, fmt)
    extracted_path = article_dir / "extracted.md"
    extracted_path.write_text(extracted)

    word_count = len(extracted.split())
    if not title:
        # Use first line or filename as title
        first_line = extracted.split("\n", 1)[0].strip().lstrip("# ")
        title = first_line[:100] if first_line else Path(filename).stem

    article = KnowledgeBaseArticle(
        id=article_id,
        filename=filename,
        title=title,
        upload_date=datetime.now(timezone.utc).isoformat(),
        tags=tags or [],
        word_count=word_count,
        format=fmt,
    )

    # Add to index
    entries = _load_index()
    entries.append(article.model_dump(exclude={"style_profile"}))
    _save_index(entries)

    return article


def save_style_profile(article_id: str, profile: StyleProfile) -> None:
    """Save a computed style profile for an article."""
    profile_path = ARTICLES_DIR / article_id / "style_profile.json"
    profile_path.write_text(profile.model_dump_json(indent=2))

    # Update index entry
    entries = _load_index()
    for entry in entries:
        if entry["id"] == article_id:
            entry["style_profile"] = profile.model_dump()
            break
    _save_index(entries)


def update_tags(article_id: str, tags: list[str]) -> Optional[KnowledgeBaseArticle]:
    """Update tags for an article."""
    entries = _load_index()
    for entry in entries:
        if entry["id"] == article_id:
            entry["tags"] = tags
            _save_index(entries)
            return KnowledgeBaseArticle.model_validate(entry)
    return None


def delete_article(article_id: str) -> bool:
    """Delete an article and its files."""
    article_dir = ARTICLES_DIR / article_id
    if article_dir.exists():
        shutil.rmtree(article_dir)

    entries = _load_index()
    new_entries = [e for e in entries if e["id"] != article_id]
    if len(new_entries) == len(entries):
        return False
    _save_index(new_entries)
    return True


def get_all_style_profiles(tags: list[str] | None = None) -> list[StyleProfile]:
    """Load all style profiles, optionally filtered by tags."""
    articles = list_articles(tags=tags)
    profiles = []
    for article in articles:
        if article.style_profile:
            profiles.append(article.style_profile)
        else:
            profile_path = ARTICLES_DIR / article.id / "style_profile.json"
            if profile_path.exists():
                profiles.append(
                    StyleProfile.model_validate_json(profile_path.read_text())
                )
    return profiles
