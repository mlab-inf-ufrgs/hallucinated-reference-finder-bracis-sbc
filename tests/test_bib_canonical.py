"""Canonical API metadata merged into .bib when verification is confident."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.extract.bib_writer import (
    merge_api_match_into_reference,
    reference_for_bib_export,
    should_use_canonical_bib_metadata,
)
from halref.models import APIMatch, APISource, Author, MatchResult, Reference


def _match(**kwargs) -> APIMatch:
    base = dict(
        source=APISource.CROSSREF,
        title="Canonical Title From API",
        authors=[Author(first="A", last="Writer", full="A Writer")],
        year=2023,
        venue="Some Conference",
        doi="10.1000/canon",
        url="",
        confidence=0.9,
    )
    base.update(kwargs)
    return APIMatch(**base)


def test_no_merge_without_best_match() -> None:
    ref = Reference(
        raw_text="x",
        title="Broken PDF Titleeeee",
        authors=[],
        year=2020,
        source_index=0,
    )
    r = MatchResult(
        reference=ref,
        best_match=None,
        title_similarity=0.0,
        hallucination_score=0.9,
    )
    assert not should_use_canonical_bib_metadata(r)
    assert reference_for_bib_export(r) is ref


def test_no_merge_when_hallucination_high() -> None:
    ref = Reference(
        raw_text="x",
        title="Broken PDF Title Here",
        authors=[Author(last="X", full="X")],
        year=2020,
        source_index=0,
    )
    m = _match()
    r = MatchResult(
        reference=ref,
        api_matches=[m],
        best_match=m,
        title_similarity=0.75,
        author_overlap=0.2,
        hallucination_score=0.85,
    )
    assert not should_use_canonical_bib_metadata(r)
    assert reference_for_bib_export(r).title == ref.title


def test_merge_when_doi_confirmed_low_score() -> None:
    ref = Reference(
        raw_text="x",
        title="pdf ocr title here",
        authors=[Author(last="X", full="X")],
        year=2019,
        doi="10.1000/canon",
        source_index=1,
        pages="1--10",
    )
    m = _match()
    r = MatchResult(
        reference=ref,
        api_matches=[m],
        best_match=m,
        title_similarity=0.4,
        author_overlap=0.0,
        hallucination_score=0.05,
    )
    assert should_use_canonical_bib_metadata(r)
    out = reference_for_bib_export(r)
    assert out.title == m.title
    assert out.year == m.year
    assert out.doi == m.doi
    assert out.pages == "1--10"


def test_merge_when_score_and_title_similarity_ok() -> None:
    ref = Reference(
        raw_text="x",
        title="Canonical Title From API",
        authors=[Author(last="Writer", full="Writer")],
        year=2023,
        source_index=0,
    )
    m = _match(venue="Fixed Venue", doi="10.1000/canon")
    r = MatchResult(
        reference=ref,
        api_matches=[m],
        best_match=m,
        title_similarity=0.95,
        author_overlap=0.8,
        hallucination_score=0.25,
    )
    assert should_use_canonical_bib_metadata(r)
    out = reference_for_bib_export(r)
    assert out.venue == "Fixed Venue"


def test_merge_strong_title_and_author_overlap() -> None:
    ref = Reference(
        raw_text="x",
        title="Canonical Title From API",
        authors=[Author(last="Writer", full="Writer")],
        year=2023,
        source_index=0,
    )
    m = _match(title="Canonical Title From API", doi="")
    r = MatchResult(
        reference=ref,
        api_matches=[m],
        best_match=m,
        title_similarity=0.9,
        author_overlap=0.5,
        hallucination_score=0.45,
    )
    assert should_use_canonical_bib_metadata(r)


def test_merge_api_match_keeps_pages() -> None:
    ref = Reference(
        raw_text="x",
        title="t",
        year=2023,
        authors=[Author(last="A", full="A")],
        pages="12--34",
        source_index=0,
    )
    m = _match()
    merged = merge_api_match_into_reference(ref, m)
    assert merged.pages == "12--34"
