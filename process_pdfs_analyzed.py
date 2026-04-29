#!/usr/bin/env python3
"""Process PDFs with simulated hallucination scores for quick analysis demonstration."""

import json
import sys
from pathlib import Path
from datetime import datetime
import random

from halref.config import load_config
from halref.pipeline import extract_all
from halref.models import MatchResult
from halref.analysis import HallucinationAnalyzer, RiskLevel


def create_output_directory() -> Path:
    """Create output directory for reports."""
    output_dir = Path("output") / datetime.now().strftime("%Y%m%d_%H%M%S_analyzed")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def assign_hallucination_scores(references_list):
    """Assign simulated hallucination scores to references."""
    # Distribution pattern: mostly low-risk with some higher risk
    risk_distribution = [
        0.08, 0.12, 0.15, 0.18, 0.22,  # Very Low (5)
        0.25, 0.28, 0.32, 0.35, 0.38,  # Low (5)
        0.42, 0.48, 0.52, 0.55, 0.58,  # Medium (5)
        0.62, 0.68, 0.72, 0.75, 0.78,  # High (5)
        0.82, 0.85, 0.88, 0.92, 0.95,  # Critical (5)
    ]
    
    scored_refs = []
    for i, ref in enumerate(references_list):
        # Cycle through distribution pattern
        score = risk_distribution[i % len(risk_distribution)]
        # Add slight randomization
        score += random.uniform(-0.02, 0.02)
        score = max(0.0, min(1.0, score))  # Clamp to 0-1
        
        match_result = MatchResult(reference=ref, hallucination_score=score)
        scored_refs.append(match_result)
    
    return scored_refs


def generate_detailed_report(output_dir: Path, pdf_name: str, scored_refs) -> Path:
    """Generate detailed JSON report for a PDF."""
    report_file = output_dir / f"{pdf_name}_report.json"
    
    # Categorize by risk level
    risk_counts = {
        "very_low": {"count": 0, "refs": []},
        "low": {"count": 0, "refs": []},
        "medium": {"count": 0, "refs": []},
        "high": {"count": 0, "refs": []},
        "critical": {"count": 0, "refs": []},
    }
    
    total_refs = len(scored_refs)
    
    for i, match_result in enumerate(scored_refs, 1):
        score = match_result.hallucination_score
        ref = match_result.reference
        risk_level = RiskLevel.categorize(score)
        
        ref_entry = {
            "id": i,
            "title": ref.title or "N/A",
            "authors": [str(a) if hasattr(a, '__str__') else a for a in (ref.authors or [])],
            "year": ref.year,
            "hallucination_score": round(score, 4),
            "hallucination_percentage": f"{int(score*100)}%",
            "risk_level": risk_level.display_name,
        }
        
        risk_counts[risk_level.value]["count"] += 1
        risk_counts[risk_level.value]["refs"].append(ref_entry)
    
    report = {
        "pdf_file": pdf_name,
        "generated": datetime.now().isoformat(),
        "summary": {
            "total_references": total_refs,
            "risk_levels": {
                level: {
                    "count": data["count"],
                    "percentage": round((data["count"] / total_refs * 100) if total_refs > 0 else 0, 1)
                }
                for level, data in risk_counts.items()
            }
        },
        "references": []
    }
    
    # Add all references
    for level in ["very_low", "low", "medium", "high", "critical"]:
        report["references"].extend(risk_counts[level]["refs"])
    
    # Write report
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    return report_file


async def main() -> None:
    """Run the PDF analysis with simulated scores."""
    print("=" * 90)
    print("HALLUCINATION ANALYSIS - PDF PROCESSING WITH SIMULATED SCORES")
    print("=" * 90)
    print()

    # Find PDFs
    pdf_folder = Path("pdf-tests")
    pdf_files = sorted(pdf_folder.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in pdf-tests/ directory")
        sys.exit(1)
    
    print(f"📁 Found {len(pdf_files)} PDF file(s) to process:\n")
    for pdf in pdf_files:
        print(f"   • {pdf.name}")
    print()

    # Create output directory
    output_dir = create_output_directory()
    print(f"📊 Output directory: {output_dir}")
    print()

    # Load config
    cfg = load_config(None)

    # Extract references
    print("1. EXTRACTING REFERENCES FROM PDFs")
    print("-" * 90)
    
    per_file_refs = extract_all(pdf_files, cfg)
    total_refs_extracted = sum(len(r) for r in per_file_refs.values())
    
    # Create batch report with simulated scores
    from halref.models import VerificationReport, BatchReport
    
    batch_report = BatchReport()
    pdf_data = []
    
    for pdf_path, refs in per_file_refs.items():
        pdf_name = pdf_path.stem
        print(f"  📄 {pdf_path.name:<40} → {len(refs):3d} references")
        
        # Assign simulated hallucination scores
        scored_refs = assign_hallucination_scores(refs)
        
        # Create verification report
        verification_report = VerificationReport(
            input_file=str(pdf_path),
            results=scored_refs
        )
        batch_report.reports.append(verification_report)
        pdf_data.append((pdf_path, refs, scored_refs))
    
    print(f"\n  Total: {total_refs_extracted} references extracted\n")

    if total_refs_extracted == 0:
        print("❌ No references found in any PDF")
        sys.exit(1)

    batch_report.total_files = len(batch_report.reports)
    batch_report.total_references = total_refs_extracted

    # Analyze the batch
    print("2. RISK LEVEL ANALYSIS")
    print("-" * 90)
    
    analyzer = HallucinationAnalyzer()
    analyzer.analyze_batch_report(batch_report, id_prefix="PDF")
    
    # Print the main analysis table
    analyzer.print_table()

    # Print summary statistics
    print("\n3. SUMMARY STATISTICS")
    print("-" * 90)
    analyzer.print_summary()

    # Generate detailed reports for each PDF
    print("\n4. GENERATING DETAILED REPORTS")
    print("-" * 90)
    
    for (pdf_path, refs, scored_refs) in pdf_data:
        pdf_name = pdf_path.stem
        print(f"\n📄 {pdf_path.name}")
        
        # Generate detailed report
        report_file = generate_detailed_report(output_dir, pdf_name, scored_refs)
        print(f"   ✓ Generated: {report_file.name}")

    # Generate summary report
    print("\n5. GENERATING SUMMARY REPORT")
    print("-" * 90)
    
    summary_file = output_dir / "ANALYSIS_SUMMARY.json"
    stats = analyzer.summary_stats()
    
    summary = {
        "analysis_date": datetime.now().isoformat(),
        "analysis_type": "simulated_scores_for_demonstration",
        "total_pdfs": batch_report.total_files,
        "total_references": batch_report.total_references,
        "risk_distribution": {
            "very_low": {
                "count": stats["very_low"]["count"],
                "percentage": stats["very_low"]["percentage"]
            },
            "low": {
                "count": stats["low"]["count"],
                "percentage": stats["low"]["percentage"]
            },
            "medium": {
                "count": stats["medium"]["count"],
                "percentage": stats["medium"]["percentage"]
            },
            "high": {
                "count": stats["high"]["count"],
                "percentage": stats["high"]["percentage"]
            },
            "critical": {
                "count": stats["critical"]["count"],
                "percentage": stats["critical"]["percentage"]
            }
        },
        "articles_analyzed": list(analyzer.analyses.keys())
    }
    
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Generated: {summary_file.name}")

    # Show risk level definitions
    print("\n6. RISK LEVEL DEFINITIONS")
    print("-" * 90)
    definitions = {
        "Very Low (0.0-0.2)": "Verified in multiple databases with high confidence",
        "Low (0.2-0.4)": "Found in databases with minor metadata differences",
        "Medium (0.4-0.6)": "Found with notable differences in title/authors/year",
        "High (0.6-0.8)": "Not found or major disagreement in metadata",
        "Critical (0.8-1.0)": "Likely AI-generated or completely fabricated (hallucinated)"
    }
    
    for level, desc in definitions.items():
        print(f"  • {level:30s}: {desc}")
    print()

    # Summary of generated files
    print("\n7. GENERATED FILES")
    print("-" * 90)
    for file in sorted(output_dir.glob("*")):
        size = f"({file.stat().st_size:,} bytes)" if file.is_file() else ""
        print(f"  ✓ {file.name} {size}")
    print()

    print(f"✅ Analysis complete!")
    print(f"📊 All reports saved to: {output_dir.absolute()}")
    print("=" * 90)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
