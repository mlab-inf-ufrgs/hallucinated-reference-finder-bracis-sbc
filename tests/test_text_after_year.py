import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.extract.field_parsers.text_after_year import strip_leading_after_year


def test_strip_after_parenthesized_year() -> None:
    assert strip_leading_after_year("). Comparative analysis.") == "Comparative analysis."
    assert strip_leading_after_year(").  Comparative analysis.") == "Comparative analysis."


def test_strip_after_plain_year() -> None:
    assert strip_leading_after_year(". Title here.") == "Title here."
