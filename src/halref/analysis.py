"""Hallucination analysis and reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from halref.models import BatchReport, VerificationReport


class RiskLevel(str, Enum):
    """Risk levels for hallucinated references."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def display_name(self) -> str:
        """Return display name with proper casing."""
        return self.value.replace("_", " ").title()

    @property
    def color(self) -> str:
        """Return ANSI color code for terminal display."""
        colors = {
            RiskLevel.VERY_LOW: "\033[92m",  # Green
            RiskLevel.LOW: "\033[94m",       # Blue
            RiskLevel.MEDIUM: "\033[93m",    # Yellow
            RiskLevel.HIGH: "\033[91m",      # Red
            RiskLevel.CRITICAL: "\033[95m",  # Magenta
        }
        return colors.get(self, "")

    @staticmethod
    def categorize(hallucination_score: float) -> RiskLevel:
        """Categorize a hallucination score into a risk level.

        Args:
            hallucination_score: Score between 0.0 and 1.0

        Returns:
            RiskLevel corresponding to the score
        """
        if hallucination_score < 0.2:
            return RiskLevel.VERY_LOW
        elif hallucination_score < 0.4:
            return RiskLevel.LOW
        elif hallucination_score < 0.6:
            return RiskLevel.MEDIUM
        elif hallucination_score < 0.8:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


@dataclass
class RiskCounts:
    """Counts for each risk level."""

    very_low: int = 0
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0

    @property
    def total(self) -> int:
        """Total references across all risk levels."""
        return self.very_low + self.low + self.medium + self.high + self.critical

    def get_count(self, level: RiskLevel) -> int:
        """Get count for a specific risk level."""
        return getattr(self, level.value)

    def increment(self, level: RiskLevel, amount: int = 1) -> None:
        """Increment count for a specific risk level."""
        current = getattr(self, level.value)
        setattr(self, level.value, current + amount)


@dataclass
class ArticleAnalysis:
    """Analysis of hallucinated references for a single article."""

    article_id: str
    counts: RiskCounts = field(default_factory=RiskCounts)

    def percentage(self, level: RiskLevel) -> float:
        """Calculate percentage for a risk level."""
        if self.counts.total == 0:
            return 0.0
        return (self.counts.get_count(level) / self.counts.total) * 100.0

    def format_cell(self, level: RiskLevel) -> str:
        """Format a cell as 'percentage%' for easy sorting and clean display."""
        percentage = self.percentage(level)
        return f"{percentage:.1f}%"

    def format_cell_with_count(self, level: RiskLevel) -> str:
        """Format a cell as 'percentage% (count)' for detailed view."""
        count = self.counts.get_count(level)
        percentage = self.percentage(level)
        return f"{percentage:.1f}% ({count})"

    def to_dict(self) -> dict:
        """Convert to dictionary for table display."""
        return {
            "Article ID": self.article_id,
            "Very Low": self.format_cell(RiskLevel.VERY_LOW),
            "Low": self.format_cell(RiskLevel.LOW),
            "Medium": self.format_cell(RiskLevel.MEDIUM),
            "High": self.format_cell(RiskLevel.HIGH),
            "Critical": self.format_cell(RiskLevel.CRITICAL),
            "Total Refs": str(self.counts.total),
        }


class HallucinationAnalyzer:
    """Analyze hallucination results and generate tables."""

    def __init__(self) -> None:
        """Initialize analyzer."""
        self.analyses: dict[str, ArticleAnalysis] = {}

    def analyze_verification_report(
        self, report: VerificationReport, article_id: str | None = None
    ) -> ArticleAnalysis:
        """Analyze a single VerificationReport.

        Args:
            report: VerificationReport to analyze
            article_id: Custom article ID (defaults to input_file)

        Returns:
            ArticleAnalysis with risk level breakdown
        """
        if article_id is None:
            article_id = report.input_file

        analysis = ArticleAnalysis(article_id=article_id)

        # Categorize each reference by risk level
        for result in report.results:
            risk_level = RiskLevel.categorize(result.hallucination_score)
            analysis.counts.increment(risk_level)

        self.analyses[article_id] = analysis
        return analysis

    def analyze_batch_report(
        self, report: BatchReport, id_prefix: str = ""
    ) -> dict[str, ArticleAnalysis]:
        """Analyze a BatchReport (multiple PDFs).

        Args:
            report: BatchReport to analyze
            id_prefix: Optional prefix for article IDs

        Returns:
            Dictionary of article_id -> ArticleAnalysis
        """
        for i, verification_report in enumerate(report.reports):
            article_id = f"{id_prefix}_{i:03d}" if id_prefix else f"Article_{i:03d}"
            self.analyze_verification_report(verification_report, article_id)

        return self.analyses

    def get_analysis(self, article_id: str) -> ArticleAnalysis | None:
        """Get analysis for a specific article."""
        return self.analyses.get(article_id)

    def table_data(self) -> list[dict]:
        """Get all analyses as list of dictionaries for table display.

        Returns:
            List of dictionaries, one per article
        """
        return [analysis.to_dict() for analysis in self.analyses.values()]

    def summary_stats(self) -> dict:
        """Get overall summary statistics.

        Returns:
            Dictionary with total counts by risk level
        """
        total_counts = RiskCounts()

        for analysis in self.analyses.values():
            total_counts.very_low += analysis.counts.very_low
            total_counts.low += analysis.counts.low
            total_counts.medium += analysis.counts.medium
            total_counts.high += analysis.counts.high
            total_counts.critical += analysis.counts.critical

        return {
            "very_low": {
                "count": total_counts.very_low,
                "percentage": (total_counts.very_low / total_counts.total * 100.0)
                if total_counts.total > 0
                else 0.0,
            },
            "low": {
                "count": total_counts.low,
                "percentage": (total_counts.low / total_counts.total * 100.0)
                if total_counts.total > 0
                else 0.0,
            },
            "medium": {
                "count": total_counts.medium,
                "percentage": (total_counts.medium / total_counts.total * 100.0)
                if total_counts.total > 0
                else 0.0,
            },
            "high": {
                "count": total_counts.high,
                "percentage": (total_counts.high / total_counts.total * 100.0)
                if total_counts.total > 0
                else 0.0,
            },
            "critical": {
                "count": total_counts.critical,
                "percentage": (total_counts.critical / total_counts.total * 100.0)
                if total_counts.total > 0
                else 0.0,
            },
            "total_articles": len(self.analyses),
            "total_references": total_counts.total,
        }

    def print_table(self) -> None:
        """Print analysis table to console using rich formatting."""
        try:
            from rich.console import Console
            from rich.table import Table
        except ImportError:
            # Fallback to simple text output if rich is not available
            self._print_table_simple()
            return

        console = Console()

        table = Table(
            title="Hallucination Risk Analysis by Article",
            show_header=True,
            header_style="bold cyan",
        )

        # Add columns
        table.add_column("Article ID", style="cyan")
        table.add_column("Very Low %", style="green", justify="right")
        table.add_column("Low %", style="blue", justify="right")
        table.add_column("Medium %", style="yellow", justify="right")
        table.add_column("High %", style="red", justify="right")
        table.add_column("Critical %", style="magenta", justify="right")
        table.add_column("Total Refs", style="white", justify="right")

        # Add rows
        for analysis in self.analyses.values():
            table.add_row(
                analysis.article_id,
                analysis.format_cell(RiskLevel.VERY_LOW),
                analysis.format_cell(RiskLevel.LOW),
                analysis.format_cell(RiskLevel.MEDIUM),
                analysis.format_cell(RiskLevel.HIGH),
                analysis.format_cell(RiskLevel.CRITICAL),
                str(analysis.counts.total),
            )

        console.print(table)

    def _print_table_simple(self) -> None:
        """Print table using simple text formatting (no rich)."""
        # Header
        print(
            f"{'Article ID':<20} {'Very Low %':<12} {'Low %':<12} {'Medium %':<12} {'High %':<12} {'Critical %':<12} {'Total':<8}"
        )
        print("-" * 100)

        # Rows
        for analysis in self.analyses.values():
            print(
                f"{analysis.article_id:<20} {analysis.format_cell(RiskLevel.VERY_LOW):<12} "
                f"{analysis.format_cell(RiskLevel.LOW):<12} {analysis.format_cell(RiskLevel.MEDIUM):<12} "
                f"{analysis.format_cell(RiskLevel.HIGH):<12} {analysis.format_cell(RiskLevel.CRITICAL):<12} "
                f"{analysis.counts.total:<8}"
            )

    def print_summary(self) -> None:
        """Print summary statistics."""
        stats = self.summary_stats()

        print("\n" + "=" * 60)
        print("HALLUCINATION RISK SUMMARY")
        print("=" * 60)
        print(f"\nTotal Articles: {stats['total_articles']}")
        print(f"Total References: {stats['total_references']}\n")

        print("Risk Level Distribution:")
        print(f"  Very Low: {stats['very_low']['count']:>3d} ({stats['very_low']['percentage']:>5.1f}%)")
        print(f"  Low:      {stats['low']['count']:>3d} ({stats['low']['percentage']:>5.1f}%)")
        print(f"  Medium:   {stats['medium']['count']:>3d} ({stats['medium']['percentage']:>5.1f}%)")
        print(f"  High:     {stats['high']['count']:>3d} ({stats['high']['percentage']:>5.1f}%)")
        print(f"  Critical: {stats['critical']['count']:>3d} ({stats['critical']['percentage']:>5.1f}%)")
        print()


def analyze_batch(batch_report: BatchReport) -> HallucinationAnalyzer:
    """Convenience function to analyze a batch report.

    Args:
        batch_report: BatchReport to analyze

    Returns:
        Configured HallucinationAnalyzer
    """
    analyzer = HallucinationAnalyzer()
    analyzer.analyze_batch_report(batch_report)
    return analyzer
