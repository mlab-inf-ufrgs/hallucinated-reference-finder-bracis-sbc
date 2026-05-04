"""Title vs journal boundary cleanup."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.extract.title_cleanup import truncate_title_at_journal_boundary


def test_truncates_advances_in_neurips() -> None:
    t = (
        "Modeling tabular data using conditional gan. "
        "Advances in neural information processing systems, 37 (2019): 1–10."
    )
    out = truncate_title_at_journal_boundary(t)
    assert out == "Modeling tabular data using conditional gan"
    assert "Advances in neural" not in out


def test_truncates_brazilian_journal() -> None:
    t = (
        "Impact of emerging technologies on digital education. "
        "Brazilian Journal of Educational Technology, 12(3): 45–60, 2021."
    )
    out = truncate_title_at_journal_boundary(t)
    assert "Brazilian Journal" not in out
    assert out.startswith("Impact of emerging technologies")


def test_truncates_journal_of_computer() -> None:
    t = (
        "Artificial intelligence in social data analysis: A case study. "
        "Journal of Computer Science, 8(2): 100–115, 2020."
    )
    out = truncate_title_at_journal_boundary(t)
    assert out.endswith("A case study")
    assert "Journal of Computer" not in out


def test_keeps_title_with_internal_periods_when_no_venue() -> None:
    t = "Deep learning. A survey of methods and applications."
    out = truncate_title_at_journal_boundary(t)
    assert out == t
