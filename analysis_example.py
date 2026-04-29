#!/usr/bin/env python3
"""Example script demonstrating hallucination scoring table generation with full reports."""

from pathlib import Path
import json
from datetime import datetime

from halref.analysis import HallucinationAnalyzer, RiskLevel
from halref.models import MatchResult, Reference, BatchReport, VerificationReport


def create_sample_data() -> BatchReport:
    """Create sample data for demonstration."""
    batch = BatchReport()

    # Article 001 - 8 references
    refs_001 = [
        MatchResult(
            reference=Reference(title="Paper A", authors=[], year=2020),
            hallucination_score=0.15,  # Very Low
        ),
        MatchResult(
            reference=Reference(title="Paper B", authors=[], year=2020),
            hallucination_score=0.35,  # Low
        ),
        MatchResult(
            reference=Reference(title="Paper C", authors=[], year=2020),
            hallucination_score=0.35,  # Low
        ),
        MatchResult(
            reference=Reference(title="Paper D", authors=[], year=2020),
            hallucination_score=0.55,  # Medium
        ),
        MatchResult(
            reference=Reference(title="Paper E", authors=[], year=2020),
            hallucination_score=0.55,  # Medium
        ),
        MatchResult(
            reference=Reference(title="Paper F", authors=[], year=2020),
            hallucination_score=0.75,  # High
        ),
        MatchResult(
            reference=Reference(title="Paper G", authors=[], year=2020),
            hallucination_score=0.85,  # Critical
        ),
        MatchResult(
            reference=Reference(title="Paper H", authors=[], year=2020),
            hallucination_score=0.95,  # Critical
        ),
    ]

    report_001 = VerificationReport(input_file="article_001.pdf", results=refs_001)
    batch.reports.append(report_001)

    # Article 002 - 6 references
    refs_002 = [
        MatchResult(
            reference=Reference(title="Paper X", authors=[], year=2021),
            hallucination_score=0.10,  # Very Low
        ),
        MatchResult(
            reference=Reference(title="Paper Y", authors=[], year=2021),
            hallucination_score=0.25,  # Low
        ),
        MatchResult(
            reference=Reference(title="Paper Z", authors=[], year=2021),
            hallucination_score=0.25,  # Low
        ),
        MatchResult(
            reference=Reference(title="Paper W", authors=[], year=2021),
            hallucination_score=0.50,  # Medium
        ),
        MatchResult(
            reference=Reference(title="Paper V", authors=[], year=2021),
            hallucination_score=0.70,  # High
        ),
        MatchResult(
            reference=Reference(title="Paper U", authors=[], year=2021),
            hallucination_score=0.88,  # Critical
        ),
    ]

    report_002 = VerificationReport(input_file="article_002.pdf", results=refs_002)
    batch.reports.append(report_002)

    # Article 003 - 10 references
    refs_003 = [
        MatchResult(
            reference=Reference(title="Paper 1", authors=[], year=2022),
            hallucination_score=0.08,
        ),
        MatchResult(
            reference=Reference(title="Paper 2", authors=[], year=2022),
            hallucination_score=0.12,
        ),
        MatchResult(
            reference=Reference(title="Paper 3", authors=[], year=2022),
            hallucination_score=0.30,
        ),
        MatchResult(
            reference=Reference(title="Paper 4", authors=[], year=2022),
            hallucination_score=0.38,
        ),
        MatchResult(
            reference=Reference(title="Paper 5", authors=[], year=2022),
            hallucination_score=0.45,
        ),
        MatchResult(
            reference=Reference(title="Paper 6", authors=[], year=2022),
            hallucination_score=0.52,
        ),
        MatchResult(
            reference=Reference(title="Paper 7", authors=[], year=2022),
            hallucination_score=0.62,
        ),
        MatchResult(
            reference=Reference(title="Paper 8", authors=[], year=2022),
            hallucination_score=0.78,
        ),
        MatchResult(
            reference=Reference(title="Paper 9", authors=[], year=2022),
            hallucination_score=0.82,
        ),
        MatchResult(
            reference=Reference(title="Paper 10", authors=[], year=2022),
            hallucination_score=0.92,
        ),
    ]

    report_003 = VerificationReport(input_file="article_003.pdf", results=refs_003)
    batch.reports.append(report_003)

    batch.total_files = 3
    batch.total_references = 24
    return batch


def create_output_directory() -> Path:
    """Create output directory for reports."""
    output_dir = Path("output") / datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_article_report(output_dir: Path, analysis: 'ArticleAnalysis', results: list) -> None:
    """Generate detailed report for a single article."""
    from halref.analysis import ArticleAnalysis
    
    report_file = output_dir / f"{analysis.article_id}_report.json"
    
    # Build detailed report
    report = {
        "article_id": analysis.article_id,
        "generated": datetime.now().isoformat(),
        "summary": {
            "total_references": analysis.counts.total,
            "risk_levels": {
                "very_low": {
                    "count": analysis.counts.very_low,
                    "percentage": analysis.percentage(RiskLevel.VERY_LOW)
                },
                "low": {
                    "count": analysis.counts.low,
                    "percentage": analysis.percentage(RiskLevel.LOW)
                },
                "medium": {
                    "count": analysis.counts.medium,
                    "percentage": analysis.percentage(RiskLevel.MEDIUM)
                },
                "high": {
                    "count": analysis.counts.high,
                    "percentage": analysis.percentage(RiskLevel.HIGH)
                },
                "critical": {
                    "count": analysis.counts.critical,
                    "percentage": analysis.percentage(RiskLevel.CRITICAL)
                }
            }
        },
        "references": []
    }
    
    # Add reference details
    for result in results:
        score = result["score"]
        risk_level = RiskLevel.categorize(score)
        
        report["references"].append({
            "id": result["id"],
            "title": result["title"],
            "hallucination_score": score,
            "hallucination_percentage": f"{int(score*100)}%",
            "risk_level": risk_level.display_name,
            "risk_level_range": {
                "very_low": "0.0-0.2",
                "low": "0.2-0.4",
                "medium": "0.4-0.6",
                "high": "0.6-0.8",
                "critical": "0.8-1.0"
            }.get(risk_level.value, "unknown")
        })
    
    # Write report
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"  ✓ Generated: {report_file.name}")


def main() -> None:
    """Run the example analysis."""
    print("=" * 80)
    print("Hallucination Scoring Analysis Example - Multi-Article")
    print("=" * 80)
    print()

    # Create output directory
    output_dir = create_output_directory()
    print(f"📁 Output directory: {output_dir}")
    print()

    # Create sample data
    batch_report = create_sample_data()

    # Analyze the batch
    analyzer = HallucinationAnalyzer()
    analyzer.analyze_batch_report(batch_report, id_prefix="Article")

    # Print the main analysis table
    print("\n1. RISK LEVEL DISTRIBUTION BY ARTICLE")
    print("-" * 80)
    analyzer.print_table()

    # Print summary statistics
    print("\n2. OVERALL SUMMARY STATISTICS")
    print("-" * 80)
    analyzer.print_summary()

    # Generate detailed reports for each article
    print("\n3. GENERATING DETAILED REPORTS")
    print("-" * 80)
    for report in batch_report.reports:
        article_id = f"Article_{batch_report.reports.index(report):03d}"
        print(f"\n📄 Processing: {article_id}")
        
        # Simulate results for this article
        results = []
        for i, result in enumerate(report.results[:18], 1):
            scores = [0.12, 0.15, 0.18, 0.22, 0.25, 0.35, 0.38, 0.42, 0.45, 0.52, 0.58, 0.65, 0.72, 0.78, 0.85, 0.88, 0.92, 0.95]
            score = scores[i - 1] if i <= len(scores) else 0.50
            
            results.append({
                "id": i,
                "title": (result.reference.title or "N/A")[:50],
                "score": score,
            })
        
        # Generate report
        analysis = analyzer.analyses[article_id]
        generate_article_report(output_dir, analysis, results)

    # Show risk level definitions
    print("\n4. RISK LEVEL DEFINITIONS")
    print("-" * 80)
    print("  Very Low  (0.0 - 0.2): Verified in multiple databases")
    print("  Low       (0.2 - 0.4): Found with minor differences")
    print("  Medium    (0.4 - 0.6): Found with notable differences")
    print("  High      (0.6 - 0.8): Not found or major disagreement")
    print("  Critical  (0.8 - 1.0): Likely AI-generated (hallucinated)")
    print()

    # Summary of generated files
    print("\n5. GENERATED FILES")
    print("-" * 80)
    for file in sorted(output_dir.glob("*.json")):
        print(f"  ✓ {file.name}")
    print()

    print(f"📊 Reports saved to: {output_dir.absolute()}")
    print("=" * 80)


if __name__ == "__main__":
    main()

