"""Author name and order comparison."""

from __future__ import annotations

import re
import unicodedata

from rapidfuzz import fuzz

from halref.models import Author

# Stricter than legacy 0.85: reduces false "same author" on fuzzy last names.
OVERLAP_LAST_NAME_THRESHOLD = 0.90
FIRST_AUTHOR_LAST_THRESHOLD = 0.93
# When both sides have a usable full/initial string, require modest agreement.
FIRST_AUTHOR_FULL_MIN_RATIO = 0.72
_NAME_PARTICLES = {"de", "da", "do", "dos", "das", "del", "di", "du", "van", "von"}


def normalize_name(name: str) -> str:
    """Normalize an author name for comparison."""
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", name)
    name = name.lower().strip()
    # Remove accents
    name = "".join(c for c in name if not unicodedata.combining(c))
    # Remove punctuation noise while preserving spaces
    name = re.sub(r"[^\w\s-]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
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


def _author_display(author: Author) -> str:
    return (author.full or f"{author.first} {author.last}").strip()


def _tokens_no_initials(s: str) -> list[str]:
    toks = [t for t in normalize_name(s).split() if t]
    # Drop isolated initials ("a", "b", ...) to handle punctuation-less names.
    return [t for t in toks if len(t) > 1 or t in _NAME_PARTICLES]


def _author_last_key(author: Author) -> str:
    """Best-effort surname key robust to punctuation-less author strings."""
    raw = normalize_name(author.last or "")
    if raw:
        parts = [p for p in raw.split() if p]
        if len(parts) >= 2 and parts[-2] in _NAME_PARTICLES:
            return f"{parts[-2]} {parts[-1]}"
        return parts[-1]

    full_tokens = _tokens_no_initials(_author_display(author))
    if not full_tokens:
        return ""
    if len(full_tokens) >= 2 and full_tokens[-2] in _NAME_PARTICLES:
        return f"{full_tokens[-2]} {full_tokens[-1]}"
    return full_tokens[-1]


def author_set_overlap(authors_a: list[Author], authors_b: list[Author]) -> float:
    """Compute Jaccard similarity of author sets based on last names.

    Returns:
        Score in [0, 1] where 1.0 = identical author sets.
    """
    if not authors_a or not authors_b:
        return 0.0

    lasts_a = [_author_last_key(a) for a in authors_a]
    lasts_b = [_author_last_key(b) for b in authors_b]
    lasts_a = [x for x in lasts_a if x]
    lasts_b = [x for x in lasts_b if x]

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

    lasts_a = [_author_last_key(a) for a in authors_a]
    lasts_b = [_author_last_key(b) for b in authors_b]
    lasts_a = [x for x in lasts_a if x]
    lasts_b = [x for x in lasts_b if x]

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


def first_author_display_similar(a: Author, b: Author, min_ratio: float = FIRST_AUTHOR_FULL_MIN_RATIO) -> bool:
    """Conservative check on the whole first-author string when both are non-trivial."""
    sa = _author_display(a)
    sb = _author_display(b)
    if len(sa) < 5 or len(sb) < 5:
        return True
    ra = normalize_name(sa)
    rb = normalize_name(sb)
    if not ra or not rb:
        return True
    # token_sort tolerates order swaps; min with ratio catches unrelated names sharing a surname token
    ts = fuzz.token_sort_ratio(ra, rb) / 100.0
    r = fuzz.ratio(ra, rb) / 100.0
    base = min(ts, r)

    # Punctuation-less exports often collapse initials ("A. B. Silva" -> "A B Silva").
    # Compare again after removing one-letter tokens.
    sa2 = " ".join(_tokens_no_initials(sa))
    sb2 = " ".join(_tokens_no_initials(sb))
    bonus = 0.0
    if sa2 and sb2:
        ts2 = fuzz.token_sort_ratio(sa2, sb2) / 100.0
        r2 = fuzz.ratio(sa2, sb2) / 100.0
        bonus = min(ts2, r2)
    return max(base, bonus) >= min_ratio


def check_first_author(authors_a: list[Author], authors_b: list[Author]) -> bool:
    """Check if the first authors match (stricter last name + whole-string check when available)."""
    if not authors_a or not authors_b:
        return True
    fa, fb = authors_a[0], authors_b[0]
    if not last_names_match(_author_last_key(fa), _author_last_key(fb), FIRST_AUTHOR_LAST_THRESHOLD):
        return False
    return first_author_display_similar(fa, fb)
