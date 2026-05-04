"""Author name and order comparison."""

from __future__ import annotations

import unicodedata

from rapidfuzz import fuzz

from halref.models import Author

# Stricter than legacy 0.85: reduces false "same author" on fuzzy last names.
OVERLAP_LAST_NAME_THRESHOLD = 0.90
FIRST_AUTHOR_LAST_THRESHOLD = 0.93
# When both sides have a usable full/initial string, require modest agreement.
FIRST_AUTHOR_FULL_MIN_RATIO = 0.72


def normalize_name(name: str) -> str:
    """Normalize an author name for comparison."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = name.lower().strip()
    # Remove accents
    name = "".join(c for c in name if not unicodedata.combining(c))
    return name


def last_names_match(a: str, b: str, threshold: float = 0.85) -> bool:
    """Check if two last names match (fuzzy)."""
    na = normalize_name(a)
    nb = normalize_name(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    return fuzz.ratio(na, nb) / 100.0 >= threshold


def author_set_overlap(authors_a: list[Author], authors_b: list[Author]) -> float:
    """Compute Jaccard similarity of author sets based on last names.

    Returns:
        Score in [0, 1] where 1.0 = identical author sets.
    """
    if not authors_a or not authors_b:
        return 0.0

    lasts_a = [normalize_name(a.last) for a in authors_a if a.last]
    lasts_b = [normalize_name(a.last) for a in authors_b if a.last]

    if not lasts_a or not lasts_b:
        return 0.0

    # Count matches using fuzzy matching
    matched_b = set()
    matches = 0
    for la in lasts_a:
        for i, lb in enumerate(lasts_b):
            if i not in matched_b and last_names_match(la, lb, OVERLAP_LAST_NAME_THRESHOLD):
                matches += 1
                matched_b.add(i)
                break

    union = len(lasts_a) + len(lasts_b) - matches
    if union == 0:
        return 0.0
    return matches / union


def check_author_order(authors_a: list[Author], authors_b: list[Author]) -> bool:
    """Check if authors appear in the same order.

    Compares the sequence of last names. Returns True if the order matches
    for all overlapping authors.
    """
    if not authors_a or not authors_b:
        return True  # Can't compare, assume OK

    lasts_a = [normalize_name(a.last) for a in authors_a if a.last]
    lasts_b = [normalize_name(a.last) for a in authors_b if a.last]

    if not lasts_a or not lasts_b:
        return True

    # Find matching pairs and check their relative order
    pairs = []
    used_b = set()
    for i, la in enumerate(lasts_a):
        for j, lb in enumerate(lasts_b):
            if j not in used_b and last_names_match(la, lb, OVERLAP_LAST_NAME_THRESHOLD):
                pairs.append((i, j))
                used_b.add(j)
                break

    if len(pairs) < 2:
        return True  # Not enough pairs to determine order

    # Check if the b-indices are monotonically increasing
    b_indices = [p[1] for p in pairs]
    return all(b_indices[i] < b_indices[i + 1] for i in range(len(b_indices) - 1))


def _first_author_display_string(author: Author) -> str:
    if (author.full or "").strip():
        return author.full.strip()
    return f"{author.first} {author.last}".strip()


def first_author_display_similar(a: Author, b: Author, min_ratio: float = FIRST_AUTHOR_FULL_MIN_RATIO) -> bool:
    """Conservative check on the whole first-author string when both are non-trivial."""
    sa = _first_author_display_string(a)
    sb = _first_author_display_string(b)
    if len(sa) < 5 or len(sb) < 5:
        return True
    ra = normalize_name(sa)
    rb = normalize_name(sb)
    if not ra or not rb:
        return True
    # token_sort tolerates order swaps; min with ratio catches unrelated names sharing a surname token
    ts = fuzz.token_sort_ratio(ra, rb) / 100.0
    r = fuzz.ratio(ra, rb) / 100.0
    return min(ts, r) >= min_ratio


def check_first_author(authors_a: list[Author], authors_b: list[Author]) -> bool:
    """Check if the first authors match (stricter last name + whole-string check when available)."""
    if not authors_a or not authors_b:
        return True
    fa, fb = authors_a[0], authors_b[0]
    if not last_names_match(fa.last, fb.last, FIRST_AUTHOR_LAST_THRESHOLD):
        return False
    return first_author_display_similar(fa, fb)
