"""Publication year vs DOI slug years."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.extract.field_parsers.year_context import pick_publication_year_match


def test_prefers_paren_year_over_doi_slug() -> None:
    s = (
        "17. Pitombeira-Neto, A.R.: An ensemble model. IEEE Access (2025). "
        "https://doi.org/10.1109/ACCESS.2025.3541385"
    )
    m = pick_publication_year_match(s)
    assert m is not None
    assert m.group(1) == "2025"
    assert m.start() < s.index("doi.org")
