"""Conservative title similarity and corroboration (hallucination scoring)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.matching.scorer import corroborating_match_count
from halref.matching.title_matcher import title_similarity, title_similarity_conservative
from halref.models import APIMatch, APISource, Author, Reference


def test_shared_buzzwords_lenient_high_conservative_low() -> None:
    a = "Digital transformation in small businesses: Challenges and opportunities"
    b = "Digital Transformation and Work 4.0"
    assert title_similarity(a, b) > 0.8
    assert title_similarity_conservative(a, b) < 0.55


def test_corroborating_count_requires_same_work() -> None:
    ref = Reference(
        raw_text="x",
        title="Digital transformation in small businesses: Challenges and opportunities",
        authors=[Author(last="Smith", first="A", full="A Smith")],
        year=2024,
    )
    m1 = APIMatch(
        source=APISource.CROSSREF,
        title="Digital Transformation and Work 4.0",
        authors=[Author(last="Jones", first="B", full="B Jones")],
        year=2023,
    )
    m2 = APIMatch(
        source=APISource.OPENALEX,
        title="Another Digital Transformation Story",
        authors=[Author(last="Lee", first="C", full="C Lee")],
        year=2022,
    )
    # Neither conservative-sim to ref is >0.7 — corroboration should be 0
    assert corroborating_match_count(ref, [m1, m2], m1) == 0
