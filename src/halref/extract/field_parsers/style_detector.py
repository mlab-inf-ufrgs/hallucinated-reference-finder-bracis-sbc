"""Detect bibliography style from reference strings."""

from __future__ import annotations

import re
from enum import Enum


class ReferenceStyle(Enum):
    """Supported bibliography styles."""
    ACL = "acl"
    SBC = "sbc"
    SPLNCS = "splncs"
    UNKNOWN = "unknown"


class StyleDetector:
    """Detect bibliography style from reference text patterns."""

    # SPLNCS: numbered references like [1], [2], etc.
    SPLNCS_NUMBERED_PATTERN = r"^\s*\[\d+\]"

    # ACL: "Last, First and First Last. YYYY."
    ACL_YEAR_AFTER_AUTHORS = (
        r"^[A-Z][A-Za-z\s,.\-'&]+?\s+(?:and\s+)?[A-Z][a-z]+\.?\s+\d{4}[a-z]?\."
    )

    # SBC: Similar to ACL but may have different formatting
    # For now, treat it the same as ACL (natbib format)
    SBC_PATTERN = r"^[A-Z][A-Za-z\s,.\-'&]+?\s+\d{4}"

    @staticmethod
    def detect_style_from_batch(references: list[str]) -> ReferenceStyle:
        """Detect dominant style from a batch of references.

        Args:
            references: List of reference strings.

        Returns:
            Detected style (ACL, SBC, SPLNCS, or UNKNOWN).
        """
        if not references:
            return ReferenceStyle.UNKNOWN

        scores = {
            ReferenceStyle.SPLNCS: 0,
            ReferenceStyle.ACL: 0,
            ReferenceStyle.SBC: 0,
        }

        for ref in references:
            if not ref.strip():
                continue

            # Check SPLNCS (numbered)
            if re.match(StyleDetector.SPLNCS_NUMBERED_PATTERN, ref):
                scores[ReferenceStyle.SPLNCS] += 2

            # Check ACL (natbib-style year after authors)
            if re.match(StyleDetector.ACL_YEAR_AFTER_AUTHORS, ref):
                scores[ReferenceStyle.ACL] += 2

            # Check SBC (year early but not in brackets)
            if re.match(StyleDetector.SBC_PATTERN, ref):
                scores[ReferenceStyle.SBC] += 1

        # Return style with highest score
        best_style = max(scores.keys(), key=lambda k: scores[k])
        if scores[best_style] > 0:
            return best_style

        return ReferenceStyle.UNKNOWN
