"""Tests for bibliography section detection and LNCS-style splitting."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.extract.ref_section import REF_HEADING, slice_reference_body
from halref.extract.splitter import split_references


def test_ref_heading_tex_style_circumflex() -> None:
    """pdfminer TeX encoding: modifier circumflex (U+02C6) instead of ê."""
    body = "Foo\n\nRefer\u02c6encias\n\nAhmad, W. et al. (2021). Title.\n"
    assert REF_HEADING.search(body)


def test_ref_heading_portuguese() -> None:
    body = "Foo bar\n\nReferências\n\n[1] Silva, J.: Title here. In: Anais (2023): pp. 1–2.\n"
    assert REF_HEADING.search(body)
    sliced = slice_reference_body(body)
    assert "[1]" in sliced
    assert "Referências" not in sliced


def test_slice_stops_at_apendice() -> None:
    body = (
        "Referências\n\n"
        "[1] A.: T. In: Proc (2020): pp. 1.\n\n"
        "Apêndice\n\nExtra text."
    )
    sliced = slice_reference_body(body)
    assert "Apêndice" not in sliced
    assert "[1]" in sliced


def test_split_numbered_eight_refs() -> None:
    # Simulates Springer / BRACIS-style blocks (one [N] per line)
    lines = [
        "Referências",
        "",
        "[1] Author, A.: First title. In: Proceedings of X (2019): pp. 1–2.",
        "[2] Author, B. and Other, C.: Second title. In: Journal Y (2020): pp. 3–4.",
        "[3] Silva, J.: Third. In: Anais (2021): pp. 5–6.",
        "[4] Costa, M.: Fourth. In: Revista (2022): pp. 7–8.",
        "[5] Lima, P.: Fifth. In: Conf (2018): pp. 9–10.",
        "[6] Santos, R.: Sixth. In: Workshop (2017): pp. 11–12.",
        "[7] Pereira, T.: Seventh. In: Book (2016): pp. 13–14.",
        "[8] Alves, U.: Eighth. In: LNCS (2015): pp. 15–16.",
    ]
    text = "\n".join(lines)
    refs = split_references(slice_reference_body(text))
    assert len(refs) == 8, f"expected 8 refs, got {len(refs)}: {refs!r}"


def test_split_includes_first_bracket_marker() -> None:
    text = (
        "[1] One, A.: Alpha. In: Proc (2019): pp. 1.\n"
        "[2] Two, B.: Beta. In: Proc (2020): pp. 2.\n"
    )
    refs = split_references(text)
    assert len(refs) == 2
    assert refs[0].startswith("[1]")
