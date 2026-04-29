"""Unit tests for risk banding and article ID parsing."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from halref.config import MatchingWeights
from halref.models import Author, MatchResult, Reference, VerificationReport
from halref.output.risk_reports import (
    article_id_from_path,
    risk_level_for_score,
    write_batch_risk_reports,
)


def test_article_id_numeric_prefix() -> None:
    assert article_id_from_path(Path("19154_Artigo.pdf")) == "19154"
    assert article_id_from_path(Path("/tmp/21132_Artigo_Completo.pdf")) == "21132"


def test_article_id_fallback() -> None:
    assert article_id_from_path(Path("PDF_000_name.pdf")) == "PDF"


def test_risk_level_boundaries() -> None:
    assert risk_level_for_score(0.0) == "Very Low"
    assert risk_level_for_score(0.2) == "Very Low"
    assert risk_level_for_score(0.21) == "Low"
    assert risk_level_for_score(0.4) == "Low"
    assert risk_level_for_score(0.41) == "Medium"
    assert risk_level_for_score(0.6) == "Medium"
    assert risk_level_for_score(0.61) == "High"
    assert risk_level_for_score(0.79) == "High"
    assert risk_level_for_score(0.8) == "Critical"
    assert risk_level_for_score(1.0) == "Critical"


def test_write_batch_smoke(tmp_path: Path) -> None:
    ref = Reference(
        title="Some paper title about machine learning",
        year=2020,
        authors=[Author(last="Smith", first="")],
        raw_text="Smith. 2020. Some paper...",
    )
    mr = MatchResult(
        reference=ref,
        api_matches=[],
        hallucination_score=0.95,
    )
    rep = VerificationReport(
        input_file=str(tmp_path / "999_Test.pdf"),
        total_references=1,
        results=[mr],
        apis_used=[],
    )
    from halref.models import BatchReport

    batch = BatchReport(reports=[rep], total_files=1, total_references=1, total_flagged=1)
    out = tmp_path / "out"
    write_batch_risk_reports(batch, out, MatchingWeights())
    assert (out / "risk_summary.md").exists()
    assert (out / "risk_summary.csv").exists()
    assert (out / "reports" / "detail_999.md").exists()
