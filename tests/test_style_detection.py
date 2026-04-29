"""Tests for bibliography style detection and parsing."""

import pytest
from src.halref.extract.field_parsers.style_detector import StyleDetector, ReferenceStyle
from src.halref.extract.field_parsers.style_specific_parsers import (
    SBCFieldParser,
    BRACISFieldParser,
)


def test_style_detection():
    """Test style detection from reference batches."""
    # SBC-style references
    sbc_refs = [
        "Smith, John and Jane Doe. 2023. A study on language models. In Proceedings of BRACIS, pages 1-10.",
        "Johnson, Robert. 2022. Deep learning approaches. In Advances in Neural Networks, volume 15.",
    ]
    detected = StyleDetector.detect_style_from_batch(sbc_refs)
    assert detected == ReferenceStyle.SBC, f"Expected SBC, got {detected}"

    # BRACIS-style references
    bracis_refs = [
        "[1] Smith, J.: A study on language models. In: Proceedings of ICML (2023): pp. 1–10.",
        "[2] Doe, J. and Johnson, R.: Deep learning approaches. In: Journal of AI (2022): pp. 50–65.",
    ]
    detected = StyleDetector.detect_style_from_batch(bracis_refs)
    assert detected == ReferenceStyle.BRACIS, f"Expected BRACIS, got {detected}"


def test_sbc_parsing():
    """Test SBC-format parsing."""
    parser = SBCFieldParser()
    raw = "Smith, John and Jane Doe. 2023. A study on language models. In Proceedings of BRACIS, pages 1-10."
    ref = parser.parse(raw)

    assert ref.year == 2023
    assert len(ref.authors) >= 1
    assert any(a.last == "Smith" for a in ref.authors)
    assert "language models" in (ref.title or "").lower()
    assert "bracis" in (ref.venue or "").lower()


def test_sbc_parenthesized_year_title_and_multi_author() -> None:
    """Vancouver / APA-style ``(YYYY). Title`` and comma-separated authors."""
    parser = SBCFieldParser()
    raw = (
        "Ahmad, W., Chowdhury, M. S. et al. (2021). Comparative analysis of machine learning. "
        "In: Case Studies in Chemical Engineering, 4:100121."
    )
    ref = parser.parse(raw)
    assert ref.year == 2021
    assert not (ref.title or "").startswith(").")
    assert "Comparative analysis" in (ref.title or "")
    assert len(ref.authors) >= 2
    assert any(a.last == "Ahmad" for a in ref.authors)
    assert any(a.last == "Chowdhury" for a in ref.authors)


def test_bracis_parsing():
    """Test BRACIS-format parsing."""
    parser = BRACISFieldParser()
    raw = "[1] Smith, J.: A study on language models. In: Proceedings of ICML (2023): pp. 1–10."
    ref = parser.parse(raw)

    assert ref.year == 2023
    assert ref.reference_number == 1
    assert len(ref.authors) >= 1
    assert ref.authors[0].last == "Smith"


def test_batch_detection():
    """Test batch detection with mixed styles."""
    mixed_refs = [
        "Smith, John. 2023. First paper.",
        "Doe, Jane. 2022. Second paper.",
        "[3] Johnson, R.: Third paper. In: Journal (2021).",
    ]
    detected = StyleDetector.detect_style_from_batch(mixed_refs)
    # Should detect either SBC (2/3) or BRACIS (1/3)
    assert detected in [ReferenceStyle.SBC, ReferenceStyle.BRACIS]
