"""
Build BibTeX string from fetched metadata (ground truth).
Single central builder: dispatches by source and formats one consistent style.
"""
from typing import Any, List, Optional
import re


def _escape(s: str) -> str:
    """Escape BibTeX special chars: \\ { }"""
    if not s:
        return ""
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _author_list_to_bibtex(authors: Any) -> str:
    """Convert authors (list or str) to BibTeX author field (Name1 and Name2)."""
    if isinstance(authors, str):
        return _escape(authors.strip())
    if isinstance(authors, list):
        return " and ".join(_escape(str(a).strip()) for a in authors if a)
    return ""


def _first_author_last_name(authors: Any) -> str:
    """Get last name (last word) of first author for key generation."""
    if isinstance(authors, str):
        parts = authors.strip().split()
        return parts[-1] if parts else "unknown"
    if isinstance(authors, list) and authors:
        first = str(authors[0]).strip()
        parts = first.split()
        return parts[-1] if parts else "unknown"
    return "unknown"


def _bibtex_key(authors: Any, year: str) -> str:
    """Generate a safe BibTeX key: LastNameYear."""
    last = _first_author_last_name(authors)
    # Alphanumeric only for key
    last = re.sub(r"[^a-zA-Z0-9]", "", last)
    y = (year or "nodate").strip()
    y = re.sub(r"[^0-9]", "", y)[:4] if y else "nodate"
    return f"{last}{y}" if last else f"ref{y}"


def build_fetched_bibtex(source: str, result: Any) -> str:
    """
    Build a BibTeX entry string from fetched metadata.
    source: 'arxiv' | 'crossref' | 'scholar' | 'semantic_scholar' | 'openalex' | 'dblp'
    result: the fetcher result object (ArxivMetadata, CrossRefResult, etc.)
    """
    title = ""
    authors: Any = []
    year = ""
    doi = ""
    url = ""
    venue = ""
    entry_type = "misc"

    if source == "arxiv":
        title = getattr(result, "title", "") or ""
        authors = getattr(result, "authors", []) or []
        year = getattr(result, "year", "") or ""  # property
        doi = getattr(result, "doi", "") or ""
        url = getattr(result, "abs_url", "") or ""
        venue = getattr(result, "journal_ref", "") or ""
        entry_type = "article" if venue else "misc"
    elif source == "crossref":
        title = getattr(result, "title", "") or ""
        authors = getattr(result, "authors", []) or []
        year = getattr(result, "year", "") or ""
        doi = getattr(result, "doi", "") or ""
        url = getattr(result, "url", "") or ""
        venue = getattr(result, "container_title", "") or ""
        entry_type = "article"
    elif source == "scholar":
        title = getattr(result, "title", "") or ""
        authors = getattr(result, "authors", "") or ""
        year = getattr(result, "year", "") or ""
        url = getattr(result, "url", "") or ""
        entry_type = "misc"
    elif source == "semantic_scholar":
        title = getattr(result, "title", "") or ""
        authors = getattr(result, "authors", []) or []
        year = getattr(result, "year", "") or ""
        url = getattr(result, "url", "") or ""
        entry_type = "misc"
    elif source == "openalex":
        title = getattr(result, "title", "") or ""
        authors = getattr(result, "authors", []) or []
        year = getattr(result, "year", "") or ""
        doi = getattr(result, "doi", "") or ""
        url = getattr(result, "url", "") or ""
        entry_type = "misc"
    elif source == "dblp":
        title = getattr(result, "title", "") or ""
        authors = getattr(result, "authors", []) or []
        year = getattr(result, "year", "") or ""
        doi = getattr(result, "doi", "") or ""
        url = getattr(result, "url", "") or ""
        entry_type = "misc"
    else:
        return ""

    key = _bibtex_key(authors, year)
    author_str = _author_list_to_bibtex(authors)

    lines = [f"  author = {{{author_str}}}", f"  title = {{{_escape(title)}}}", f"  year = {{{year or '?'}}}"]
    if venue:
        lines.append(f"  journal = {{{_escape(venue)}}}")
    if doi:
        lines.append(f"  doi = {{{_escape(doi)}}}")
    if url:
        lines.append(f"  url = {{{_escape(url)}}}")
    lines.append(f"  note = {{Fetched from {source}}}")

    return f"@{entry_type}{{{key},\n" + ",\n".join(lines) + "\n}"
