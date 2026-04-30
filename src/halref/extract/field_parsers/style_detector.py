"""Detect bibliography style from reference strings."""

from __future__ import annotations

import re
from enum import Enum


class ReferenceStyle(Enum):
    """Supported bibliography styles."""
    SBC = "sbc"
    BRACIS = "bracis"
    UNKNOWN = "unknown"


class StyleDetector:
    """Detect bibliography style from reference text patterns."""

    # BRACIS / Springer: [1] ... or "1. Author, A.: ..."
    BRACIS_NUMBERED_PATTERN = r"^\s*\[\d+\]"
    BRACIS_DOT_NUMBERED_PATTERN = r"^\s*\d{1,3}\.\s+[A-Z\u00C0-\u024F]"

    # SBC: natbib format with year after authors
    # "Last, First and First Last. YYYY."
    SBC_PATTERN = r"^[A-Z][A-Za-z\s,.\-'&]+?\s+\d{4}"

    @staticmethod
    def detect_style_from_batch(references: list[str]) -> ReferenceStyle:
        """Detect dominant style from a batch of references.

        Args:
            references: List of reference strings.

        Returns:
            Detected style (SBC, BRACIS, or UNKNOWN).
        """
        if not references:
            return ReferenceStyle.UNKNOWN

        scores = {
            ReferenceStyle.BRACIS: 0,
            ReferenceStyle.SBC: 0,
        }

        for ref in references:
            if not ref.strip():
                continue

            # Check BRACIS (numbered)
            if re.match(StyleDetector.BRACIS_NUMBERED_PATTERN, ref):
                scores[ReferenceStyle.BRACIS] += 2
            if re.match(StyleDetector.BRACIS_DOT_NUMBERED_PATTERN, ref):
                scores[ReferenceStyle.BRACIS] += 2

            # Check SBC (natbib-style with year)
            if re.match(StyleDetector.SBC_PATTERN, ref):
                scores[ReferenceStyle.SBC] += 2

        # Return style with highest score
        best_style = max(scores.keys(), key=lambda k: scores[k])
        if scores[best_style] > 0:
            return best_style

        return ReferenceStyle.UNKNOWN
