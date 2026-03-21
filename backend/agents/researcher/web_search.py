"""Web search and content fetching for the Researcher agent."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from shared.config import MAX_SEARCH_RESULTS, MAX_PAGE_CONTENT_LENGTH, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str


@dataclass
class FetchedPage:
    url: str
    title: str
    text_content: str


async def search_web(query: str, num_results: int = MAX_SEARCH_RESULTS) -> list[SearchResult]:
    """Search the web using googlesearch-python."""
    results: list[SearchResult] = []
    try:
        from googlesearch import search as gsearch

        urls = list(gsearch(query, num_results=num_results, advanced=True))
        for r in urls:
            results.append(SearchResult(
                url=r.url,
                title=r.title or "",
                snippet=r.description or "",
            ))
    except Exception as e:
        logger.error(f"Web search failed for '{query}': {e}")
    return results


async def fetch_page_content(url: str) -> FetchedPage | None:
    """Fetch and extract text content from a URL."""
    try:
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (research-agent)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return None
            html = resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None

    return extract_text(url, html)


def extract_text(url: str, html: str) -> FetchedPage:
    """Extract clean text from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # Extract text from main content areas first, fall back to body
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main is None:
        main = soup

    text = main.get_text(separator="\n", strip=True)

    # Truncate to max length
    if len(text) > MAX_PAGE_CONTENT_LENGTH:
        text = text[:MAX_PAGE_CONTENT_LENGTH] + "\n[...truncated]"

    return FetchedPage(url=url, title=title, text_content=text)
