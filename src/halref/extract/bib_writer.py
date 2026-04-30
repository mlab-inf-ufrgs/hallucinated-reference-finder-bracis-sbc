"""Write Reference objects to BibTeX format."""

from __future__ import annotations

import re
from pathlib import Path

from halref.models import APIMatch, MatchResult, Reference

# When verification is confident, BibTeX fields are taken from the API match
# (canonical metadata) instead of noisy PDF parsing. Tuned conservatively.
_CANONICAL_VERY_LOW_SCORE = 0.14  # e.g. DOI-confirmed (scorer uses ~0.05)
_CANONICAL_MAX_SCORE = 0.38
_CANONICAL_MIN_TITLE_SIM = 0.72
_STRONG_TITLE_SIM = 0.87
_STRONG_AUTHOR_OVERLAP = 0.46
_STRONG_PAIR_MAX_SCORE = 0.50


def merge_api_match_into_reference(ref: Reference, match: APIMatch) -> Reference:
    """Build a Reference using API metadata, keeping PDF-only fields where needed."""
    return ref.model_copy(
        update={
            "title": (match.title or ref.title or "").strip() or ref.title,
            "authors": match.authors if match.authors else ref.authors,
            "year": match.year if match.year is not None else ref.year,
            "venue": (match.venue or ref.venue or "").strip() or ref.venue,
            "doi": (match.doi or ref.doi or "").strip() or ref.doi,
            "url": (match.url or ref.url or "").strip() or ref.url,
            # pages rarely come from APIs in our model — keep PDF
            "pages": ref.pages,
        }
    )


def should_use_canonical_bib_metadata(result: MatchResult) -> bool:
    """True when verified API match is trustworthy enough to drive BibTeX fields."""
    m = result.best_match
    if m is None:
        return False
    title_api = (m.title or "").strip()
    if len(title_api) < 8 and not (result.reference.title or "").strip():
        return False

    s = result.hallucination_score
    ts = result.title_similarity
    ao = result.author_overlap

    if s <= _CANONICAL_VERY_LOW_SCORE:
        return True
    if s <= _CANONICAL_MAX_SCORE and ts >= _CANONICAL_MIN_TITLE_SIM:
        return True
    if (
        ts >= _STRONG_TITLE_SIM
        and ao >= _STRONG_AUTHOR_OVERLAP
        and s <= _STRONG_PAIR_MAX_SCORE
    ):
        return True
    return False


def reference_for_bib_export(result: MatchResult) -> Reference:
    """Reference row to serialize in .bib: PDF parse, or merged API metadata if confident."""
    ref = result.reference
    m = result.best_match
    if m is None or not should_use_canonical_bib_metadata(result):
        return ref
    merged = merge_api_match_into_reference(ref, m)
    if not _is_valid_for_bib(merged):
        return ref
    return merged


def write_bib_from_match_results(
    results: list[MatchResult],
    output_path: Path,
    quiet: bool = False,
) -> None:
    """Write one .bib per verification results, preferring canonical API fields when confident."""
    entries = []
    skipped = 0
    for result in results:
        ref = reference_for_bib_export(result)
        if not _is_valid_for_bib(ref):
            skipped += 1
            continue
        entry = reference_to_bibtex(ref)
        if entry:
            entries.append(entry)

    output_path = Path(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(entries))
        f.write("\n")

    if not quiet:
        from rich.console import Console

        msg = f"Wrote {len(entries)} references to {output_path.resolve()}"
        if skipped:
            msg += f" ({skipped} invalid entries skipped)"
        Console(stderr=True).print(msg)


def write_bib(references: list[Reference], output_path: Path, quiet: bool = False) -> None:
    """Write references to a .bib file, skipping invalid entries."""
    entries = []
    skipped = 0
    for ref in references:
        if not _is_valid_for_bib(ref):
            skipped += 1
            continue
        entry = reference_to_bibtex(ref)
        if entry:
            entries.append(entry)

    output_path = Path(output_path)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(entries))
        f.write("\n")

    if not quiet:
        from rich.console import Console
        msg = f"Wrote {len(entries)} references to {output_path.resolve()}"
        if skipped:
            msg += f" ({skipped} invalid entries skipped)"
        Console(stderr=True).print(msg)


def _is_valid_for_bib(ref: Reference) -> bool:
    """Check if a reference has enough valid data to include in a .bib file.

    Rejects entries that would produce nonsensical BibTeX:
    - No title at all
    - Single-word titles (truncated extraction)
    - Title that is clearly an author list (no verbs/nouns, just names and commas)
    - No year AND no authors (not enough to identify the work)
    """
    title = (ref.title or "").strip()

    # Must have a title
    if not title:
        return False

    # Title must be more than one word (single word = truncated)
    if len(title.split()) <= 1:
        return False

    # Title should be at least ~15 chars to be meaningful
    if len(title) < 15:
        return False

    # Reject if title looks like an author list (names + commas, no real title content)
    # Heuristic: mostly commas and capitalized words, no period or colon
    if not ref.year and "." not in title and ":" not in title:
        comma_count = title.count(",")
        word_count = len(title.split())
        if comma_count >= 2 and comma_count >= word_count * 0.3:
            return False

    # Must have EITHER a year OR authors to be minimally useful
    if not ref.year and not ref.authors:
        return False

    return True


def reference_to_bibtex(ref: Reference) -> str:
    """Convert a Reference to a BibTeX entry string."""
    # Generate a citation key
    key = _make_cite_key(ref)

    # Determine entry type
    entry_type = _guess_entry_type(ref)

    fields = []
    if ref.title:
        fields.append(f"  title = {{{ref.title}}}")
    if ref.authors:
        author_str = " and ".join(str(a) for a in ref.authors)
        fields.append(f"  author = {{{author_str}}}")
    if ref.year:
        fields.append(f"  year = {{{ref.year}}}")
    if ref.venue:
        if entry_type == "article":
            fields.append(f"  journal = {{{ref.venue}}}")
        else:
            fields.append(f"  booktitle = {{{ref.venue}}}")
    if ref.pages:
        fields.append(f"  pages = {{{ref.pages}}}")
    if ref.doi:
        fields.append(f"  doi = {{{ref.doi}}}")
    if ref.url:
        fields.append(f"  url = {{{ref.url}}}")

    if not fields:
        return ""

    fields_str = ",\n".join(fields)
    return f"@{entry_type}{{{key},\n{fields_str}\n}}"


def _make_cite_key(ref: Reference) -> str:
    """Generate a BibTeX citation key."""
    parts = []

    # First author last name
    if ref.authors:
        last = ref.authors[0].last or ref.authors[0].full.split()[-1] if ref.authors[0].full else "unknown"
        last = re.sub(r"[^a-zA-Z]", "", last).lower()
        parts.append(last)
    else:
        parts.append("unknown")

    # Year
    if ref.year:
        parts.append(str(ref.year))

    # First significant word of title
    if ref.title:
        words = re.findall(r"[a-zA-Z]+", ref.title.lower())
        stop_words = {"a", "an", "the", "of", "in", "on", "for", "to", "and", "with", "is", "are"}
        for w in words:
            if w not in stop_words and len(w) > 2:
                parts.append(w)
                break

    return "-".join(parts) if parts else f"ref-{ref.source_index}"


def _guess_entry_type(ref: Reference) -> str:
    """Guess the BibTeX entry type from venue text."""
    venue_lower = ref.venue.lower() if ref.venue else ""

    if any(kw in venue_lower for kw in ("proceedings", "conference", "workshop", "symposium")):
        return "inproceedings"
    if any(kw in venue_lower for kw in ("journal", "transactions", "review", "letters")):
        return "article"
    if "arxiv" in venue_lower or "preprint" in venue_lower:
        return "misc"
    if any(kw in venue_lower for kw in ("book", "press", "publisher", "edition")):
        return "inbook"
    if "thesis" in venue_lower or "dissertation" in venue_lower:
        return "phdthesis"

    # Default to inproceedings for ACL papers
    return "inproceedings"
