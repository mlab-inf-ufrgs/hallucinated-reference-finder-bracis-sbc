"""Strip trailing journal / venue clauses mistakenly merged into the title field."""

from __future__ import annotations

import re

# First segment after a sentence boundary that clearly starts venue metadata,
# not a continuation of the paper title (English + common BR venues).
_VENUE_SEGMENT_PREFIXES: tuple[str, ...] = (
    "advances in neural",
    "advances in ",
    "proceedings of the",
    "proceedings of ",
    "proceedings ",
    "journal of ",
    "ieee ",
    "acm ",
    "transactions on ",
    "transactions of ",
    "nature communications",
    "nature machine intelligence",
    "science advances",
    "springer",
    "elsevier",
    "wiley",
    "brazilian journal",
    "international journal of",
    "lecture notes in computer science",
    "foundations and trends",
    "pattern recognition",
    "information sciences",
    "neurocomputing",
    "knowledge-based systems",
    "expert systems with applications",
    "machine learning ",
    "statistical science",
    "annals of ",
    "communications of the acm",
    "frontiers in ",
    "arxiv",
    "corr abs",
    "openreview",
)


def _segment_looks_like_venue_start(segment: str) -> bool:
    s = segment.strip().lower()
    if len(s) < 10:
        return False
    for p in _VENUE_SEGMENT_PREFIXES:
        if s.startswith(p):
            return True
    # Generic: "Journal of …", "Annual … Conference", "International Conference on …"
    if re.match(
        r"^(journal|transactions|proceedings|annual|international conference|"
        r"conference on|workshop on|symposium on)\b",
        s,
    ):
        return True
    # Venue line with volume + year in first chunk: ", 37 (2019" or " 32 (2020"
    if re.search(r",\s*\d{1,3}\s*\(\d{4}\)", s[:100]):
        return True
    if re.match(r"^pp\.?\s*\d", s):
        return True
    return False


def truncate_title_at_journal_boundary(title: str) -> str:
    """If ``title`` contains ``Title. JournalName…``, keep only the paper title part.

    Uses the same sentence split as BRACIS (do not break on single-letter initials
    like ``B. C.``). Stops at the first segment that looks like a journal or
    proceedings line — avoids pulling venue into Crossref queries.

    Titles with multiple real sentences but *no* following venue segment are kept
    intact (no segment matches venue heuristics).
    """
    t = (title or "").strip()
    if not t or len(t) < 25:
        return t

    parts = re.split(r"(?<![A-Z])\.\s+", t)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) < 2:
        return t

    for i in range(1, len(parts)):
        if _segment_looks_like_venue_start(parts[i]):
            out = ". ".join(parts[:i]).strip()
            return out if len(out) >= 12 else t

    return t
