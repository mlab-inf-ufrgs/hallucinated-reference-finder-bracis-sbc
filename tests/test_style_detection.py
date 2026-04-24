"""Tests for bibliography style detection and parsing."""

import pytest
from src.halref.extract.field_parsers.style_detector import StyleDetector, ReferenceStyle
from src.halref.extract.field_parsers.style_specific_parsers import (
    ACLFieldParser,
    SBCFieldParser,
    SPLNCSFieldParser,
)


def test_style_detection():
    """Test style detection from reference batches."""
    # ACL-style references
    acl_refs = [
        "Smith, John and Jane Doe. 2023. A study on language models. In Proceedings of ACL, pages 1-10.",
        "Johnson, Robert. 2022. Deep learning approaches. In Advances in Neural Networks, volume 15.",
    ]
    detected = StyleDetector.detect_style_from_batch(acl_refs)
    assert detected in [ReferenceStyle.ACL, ReferenceStyle.SBC], f"Expected ACL or SBC, got {detected}"

    # SPLNCS-style references
    splncs_refs = [
        "[1] Smith, J.: A study on language models. In: Proceedings of ICML (2023): pp. 1–10.",
        "[2] Doe, J. and Johnson, R.: Deep learning approaches. In: Journal of AI (2022): pp. 50–65.",
    ]
    detected = StyleDetector.detect_style_from_batch(splncs_refs)
    assert detected == ReferenceStyle.SPLNCS, f"Expected SPLNCS, got {detected}"


def test_acl_parsing():
    """Test ACL-format parsing."""
    parser = ACLFieldParser()
    raw = "Smith, John and Jane Doe. 2023. A study on language models. In Proceedings of ACL, pages 1-10."
    ref = parser.parse(raw)

    assert ref.year == 2023
    assert len(ref.authors) >= 1
    assert any(a.last == "Smith" for a in ref.authors)
    assert "language models" in (ref.title or "").lower()
    assert "acl" in (ref.venue or "").lower()


def test_splncs_parsing():
    """Test SPLNCS-format parsing."""
    parser = SPLNCSFieldParser()
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
    # Should detect either ACL (2/3) or SPLNCS (1/3)
    assert detected in [ReferenceStyle.ACL, ReferenceStyle.SBC, ReferenceStyle.SPLNCS]
