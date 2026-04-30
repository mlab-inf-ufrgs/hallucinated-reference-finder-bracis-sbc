"""Pick publication year vs years embedded in DOIs / IEEE-style slugs."""

from __future__ import annotations

import re

# e.g. .../ACCESS.2025.3541385 — the 2025 is not the publication year for splitting
_SLUG_YEAR = re.compile(r"/[A-Za-z0-9.\-]{2,50}\.(19|20)\d{2}\.[0-9A-Za-z]")
_WORD_YEAR = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")
_PARENS_YEAR = re.compile(r"\(((?:19|20)\d{2})\)")


def year_in_doi_or_journal_slug(text: str, m: re.Match[str]) -> bool:
    """True if this ``\\bYYYY\\b`` match sits inside a DOI-like ``/TOKEN.YYYY.`` segment."""
    lo = max(0, m.start() - 120)
    hi = min(len(text), m.end() + 40)
    return _SLUG_YEAR.search(text[lo:hi]) is not None


def pick_publication_year_match(text: str) -> re.Match[str] | None:
    """Prefer ``(YYYY)`` (Springer / BRACIS); else first plain year not inside a DOI slug."""
    for pm in reversed(list(_PARENS_YEAR.finditer(text))):
        y = int(pm.group(1))
        if 1900 <= y <= 2099:
            return pm
    for wm in _WORD_YEAR.finditer(text):
        if year_in_doi_or_journal_slug(text, wm):
            continue
        return wm
    return None
