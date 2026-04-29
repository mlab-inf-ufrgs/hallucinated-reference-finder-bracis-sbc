"""Strip punctuation between a matched publication year and the paper title."""

from __future__ import annotations

import re

# After "2021" or "2021)" in "(2021). Title" — remove leading ), ], dots, spaces.
_LEADING_JUNK_AFTER_YEAR = re.compile(r"^[\s\)\]\.,]+")


def strip_leading_after_year(text: str) -> str:
    """Remove ``).``, ``).``, stray brackets, etc. before the title starts."""
    return _LEADING_JUNK_AFTER_YEAR.sub("", text.strip())
