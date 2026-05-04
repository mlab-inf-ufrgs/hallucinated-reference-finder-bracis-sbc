"""Aggregate risk summary and per-article Markdown detail reports."""

from __future__ import annotations

import csv
import re
from collections import Counter
from pathlib import Path

from halref.config import MatchingWeights
from halref.matching.scorer import corroborating_match_count
from halref.models import BatchReport, MatchResult, VerificationReport

# Hallucination score → risk band (same bands as the upstream README / UI).
def risk_level_for_score(score: float) -> str:
    if score <= 0.2:
        return "Very Low"
    if score <= 0.4:
        return "Low"
    if score <= 0.6:
        return "Medium"
    if score < 0.8:
        return "High"
    return "Critical"


def article_id_from_path(pdf_path: Path) -> str:
    """Leading numeric ID (e.g. 19154 from 19154_Artigo.pdf), else first segment before underscore."""
    stem = pdf_path.stem
    m = re.match(r"^(\d+)", stem)
    if m:
        return m.group(1)
    if "_" in stem:
        return stem.split("_", 1)[0]
    return stem


def _safe_filename_fragment(article_id: str) -> str:
    s = re.sub(r"[^\w.\-]+", "_", article_id, flags=re.UNICODE).strip("_")
    return s[:120] or "unknown"


def _high_conf_match_count(result: MatchResult) -> int:
    """Aligned with scorer: corroborating sources for the same work as best_match."""
    return corroborating_match_count(
        result.reference,
        result.api_matches,
        result.best_match,
    )


def _signal(result: MatchResult, name: str):
    for s in result.signals:
        if s.name == name:
            return s
    return None


def _author_order_summary(result: MatchResult) -> str:
    if not result.reference.authors and not (result.best_match and result.best_match.authors):
        return "—"
    if result.first_author_match and result.author_order_correct:
        return "OK"
    if not result.first_author_match:
        return "Wrong first author"
    return "Order differs"


def _year_summary(result: MatchResult) -> str:
    s = _signal(result, "year_mismatch")
    if result.year_match:
        return "Match"
    if s and s.description:
        return s.description
    return "Mismatch / unknown"


def _consensus_summary(result: MatchResult) -> str:
    n = _high_conf_match_count(result)
    apis = len(result.api_matches)
    s = _signal(result, "low_api_consensus")
    base = f"{n} corroborating source(s) (strict title + same work as best) / {apis} raw match(es)"
    if s and s.description:
        return f"{base}; {s.description}"
    return base


def _why_classification(result: MatchResult, weights: MatchingWeights) -> str:
    """Human-readable rationale from weighted signals."""
    lines: list[str] = []
    if _signal(result, "doi_match"):
        lines.append("DOI matched a database record — treated as verified.")
        return "\n".join(lines)
    if not result.api_matches:
        lines.append("No database match — not found in any configured API.")
        return "\n".join(lines)

    scored = [
        (s.description or s.name, s.value * s.weight, s.name)
        for s in result.signals
        if s.weight > 0 and s.value > 0.01
    ]
    scored.sort(key=lambda x: -x[1])
    for desc, contrib, _ in scored[:6]:
        lines.append(f"- {desc} (weighted contribution ≈ {contrib:.3f})")
    if not lines:
        lines.append("- All checked signals are low; score dominated by small combined effects.")
    return "\n".join(lines)


def _excerpt(text: str, max_len: int = 70) -> str:
    t = (text or "").replace("\n", " ").strip()
    t = t.replace("|", "/")
    if len(t) <= max_len:
        return t or "—"
    return t[: max_len - 1] + "…"


def _risk_histogram(results: list[MatchResult]) -> Counter[str]:
    c: Counter[str] = Counter()
    for r in results:
        c[risk_level_for_score(r.hallucination_score)] += 1
    return c


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return 100.0 * part / whole


def write_batch_risk_reports(
    batch: BatchReport,
    outdir: Path,
    weights: MatchingWeights,
) -> None:
    """Write ``risk_summary.md``, ``risk_summary.csv``, and ``reports/detail_<id>.md``."""
    outdir.mkdir(parents=True, exist_ok=True)
    reports_dir = outdir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    order = ["Very Low", "Low", "Medium", "High", "Critical"]
    rows: list[dict[str, str | int | float]] = []

    for rep in batch.reports:
        pdf_path = Path(rep.input_file)
        aid = article_id_from_path(pdf_path)
        hist = _risk_histogram(rep.results)
        total = len(rep.results)
        row: dict[str, str | int | float] = {"Article ID": aid, "Total": total}
        for level in order:
            row[level] = round(_pct(hist[level], total), 1)
        rows.append(row)

        _write_per_article_markdown(rep, aid, pdf_path, weights, reports_dir)

    _write_summary_md(outdir / "risk_summary.md", rows, order)
    _write_summary_csv(outdir / "risk_summary.csv", rows, order)


def _write_summary_md(path: Path, rows: list[dict], order: list[str]) -> None:
    cols = ["Article ID"] + order + ["Total"]
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [
        "# Hallucination risk summary (per article)",
        "",
        "Percentages are the share of **references** in that PDF falling in each risk band "
        "(hallucination score).",
        "",
        header,
        sep,
    ]
    for row in rows:
        cells = [str(row["Article ID"])]
        for level in order:
            cells.append(f"{row[level]:.1f}%")
        cells.append(str(int(row["Total"])))
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "| Level | Score | Meaning |",
            "|-------|-------|---------|",
            "| **Very Low** | 0.0–0.2 | Verified in multiple databases |",
            "| **Low** | 0.2–0.4 | Found with minor differences |",
            "| **Medium** | 0.4–0.6 | Found with notable differences |",
            "| **High** | 0.6–0.8 | Not found or major disagreement |",
            "| **Critical** | 0.8–1.0 | Likely AI-generated (hallucinated) |",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary_csv(path: Path, rows: list[dict], order: list[str]) -> None:
    fieldnames = ["Article ID"] + order + ["Total"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row[k] for k in fieldnames})


def _write_per_article_markdown(
    rep: VerificationReport,
    article_id: str,
    pdf_path: Path,
    weights: MatchingWeights,
    reports_dir: Path,
) -> None:
    fname = f"detail_{_safe_filename_fragment(article_id)}.md"
    lines: list[str] = [
        f"# Per-reference report — Article ID **{article_id}**",
        "",
        f"- **File:** `{pdf_path.name}`",
        f"- **Path:** `{rep.input_file}`",
        f"- **References:** {rep.total_references}",
        f"- **APIs used:** {', '.join(rep.apis_used) if rep.apis_used else '—'}",
        "",
        "## Scoring components (weights)",
        "",
        "| Weight | Component | Meaning |",
        "|--------|-----------|---------|",
        f"| **{weights.title:.0%}** | Title match | Similarity of extracted vs. database title |",
        f"| **{weights.authors:.0%}** | Authors | Overlap of author names with matched paper |",
        f"| **{weights.author_order:.0%}** | Author order | First author and ordering vs. match |",
        f"| **{weights.year:.0%}** | Year | Publication year agreement |",
        f"| **{weights.consensus:.0%}** | Consensus | Agreement across multiple API matches |",
        "",
        "Hallucination score = weighted sum of **mismatch** signals (higher = more suspicious).",
        "",
        "## References",
        "",
        "| # | Title (extracted) | Title match | Authors | Author order | Year | Consensus | Score | Level |",
        "|---|-------------------|-------------|---------|--------------|------|-----------|-------|-------|",
    ]

    for i, r in enumerate(rep.results, start=1):
        ref = r.reference
        title_ex = _excerpt(ref.title or ref.raw_text, 56)
        t_match = f"{r.title_similarity:.0%}" if r.api_matches else "—"
        auth = f"{r.author_overlap:.0%}" if r.api_matches else "—"
        ord_s = _author_order_summary(r) if r.api_matches else "—"
        yr = _year_summary(r)
        cons = _consensus_summary(r)
        score = f"{r.hallucination_score:.2f}"
        lvl = risk_level_for_score(r.hallucination_score)
        lines.append(
            f"| {i} | {title_ex} | {t_match} | {auth} | {ord_s} | {yr} | {cons} | {score} | **{lvl}** |"
        )

    lines.append("")
    lines.append("## Why this risk level (per reference)")
    lines.append("")

    for i, r in enumerate(rep.results, start=1):
        ref = r.reference
        title_ex = _excerpt(ref.title or ref.raw_text, 80)
        lvl = risk_level_for_score(r.hallucination_score)
        lines.append(f"### {i}. {title_ex}")
        lines.append("")
        lines.append(f"- **Hallucination score:** {r.hallucination_score:.3f} → **{lvl}**")
        if r.best_match:
            src = r.best_match.source
            src_s = getattr(src, "value", str(src))
            lines.append(
                f"- **Best API title:** {_excerpt(r.best_match.title, 100)} ({src_s})"
            )
        lines.append("")
        lines.append(_why_classification(r, weights))
        lines.append("")

    (reports_dir / fname).write_text("\n".join(lines), encoding="utf-8")
