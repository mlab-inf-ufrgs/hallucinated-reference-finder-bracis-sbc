#!/usr/bin/env python3
"""Process real PDF files from pdf-tests/ and generate hallucination analysis reports."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from halref.models import BatchReport
from halref.config import load_config
from halref.pipeline import extract_all, run_check
from halref.analysis import HallucinationAnalyzer, RiskLevel


def create_output_directory() -> Path:
    """Create output directory for reports."""
    output_dir = Path("output") / datetime.now().strftime("%Y%m%d_%H%M%S_real_pdfs")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def generate_detailed_report(
    output_dir: Path, 
    file_report,
) -> None:
    """Generate detailed JSON report for a single PDF."""
    pdf_name = Path(file_report.input_file).stem
    report_file = output_dir / f"{pdf_name}_detailed_report.json"
    
    # Categorize references by risk level
    risk_counts = {
        "very_low": {"count": 0, "refs": []},
        "low": {"count": 0, "refs": []},
        "medium": {"count": 0, "refs": []},
        "high": {"count": 0, "refs": []},
        "critical": {"count": 0, "refs": []},
    }
    
    # Build detailed report
    for i, result in enumerate(file_report.results, 1):
        score = result.hallucination_score
        risk_level = RiskLevel.categorize(score)
        
        ref_entry = {
            "id": i,
            "title": result.reference.title or "N/A",
            "authors": result.reference.authors or [],
            "year": result.reference.year,
            "hallucination_score": round(score, 4),
            "hallucination_percentage": f"{int(score*100)}%",
            "risk_level": risk_level.display_name,
        }
        
        risk_counts[risk_level.value]["count"] += 1
        risk_counts[risk_level.value]["refs"].append(ref_entry)
    
    total_refs = len(file_report.results)
    
    detailed_report = {
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
    
    # Add references organized by risk level
    for level in ["very_low", "low", "medium", "high", "critical"]:
        detailed_report["references"].extend(risk_counts[level]["refs"])
    
    # Write report
    with open(report_file, "w") as f:
        json.dump(detailed_report, f, indent=2)
    
    return report_file


async def main() -> None:
    """Run the PDF processing pipeline."""
    print("=" * 90)
    print("HALLUCINATION ANALYSIS - REAL PDF PROCESSING")
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

    # Process PDFs
    print("1. EXTRACTING REFERENCES FROM PDFs")
    print("-" * 90)
    
    # Extract references
    per_file_refs = extract_all(pdf_files, cfg)
    total_refs_extracted = sum(len(r) for r in per_file_refs.values())
    
    for pdf_path, refs in per_file_refs.items():
        print(f"  📄 {pdf_path.name:<40} → {len(refs):3d} references")
    
    print(f"\n  Total: {total_refs_extracted} references extracted\n")

    if total_refs_extracted == 0:
        print("❌ No references found in any PDF")
        sys.exit(1)

    # Verify references
    print("2. VERIFYING REFERENCES AGAINST APIS")
    print("-" * 90)
    
    report = await run_check(pdf_files, cfg, threshold=0.0, per_file_refs=per_file_refs)
    
    print(f"  Verification complete: {report.total_references} references checked\n")

    # Analyze the batch
    print("3. RISK LEVEL ANALYSIS")
    print("-" * 90)
    
    analyzer = HallucinationAnalyzer()
    analyzer.analyze_batch_report(report, id_prefix="PDF")
    
    # Print the main analysis table
    analyzer.print_table()

    # Print summary statistics
    print("\n4. SUMMARY STATISTICS")
    print("-" * 90)
    analyzer.print_summary()

    # Generate detailed reports for each PDF
    print("\n5. GENERATING DETAILED REPORTS")
    print("-" * 90)
    
    generated_files = []
    for file_report in report.reports:
        pdf_name = Path(file_report.input_file).name
        print(f"\n📄 {pdf_name}")
        
        # Generate detailed report
        report_file = generate_detailed_report(output_dir, file_report)
        print(f"   ✓ Generated: {report_file.name}")
        generated_files.append(report_file)

    # Generate summary report
    print("\n6. GENERATING SUMMARY REPORT")
    print("-" * 90)
    
    summary_file = output_dir / "ANALYSIS_SUMMARY.json"
    summary = {
        "analysis_date": datetime.now().isoformat(),
        "total_pdfs": report.total_files,
        "total_references": report.total_references,
        "risk_distribution": {
            "very_low": {
                "count": analyzer.summary_stats()["very_low_count"],
                "percentage": analyzer.summary_stats()["very_low_pct"]
            },
            "low": {
                "count": analyzer.summary_stats()["low_count"],
                "percentage": analyzer.summary_stats()["low_pct"]
            },
            "medium": {
                "count": analyzer.summary_stats()["medium_count"],
                "percentage": analyzer.summary_stats()["medium_pct"]
            },
            "high": {
                "count": analyzer.summary_stats()["high_count"],
                "percentage": analyzer.summary_stats()["high_pct"]
            },
            "critical": {
                "count": analyzer.summary_stats()["critical_count"],
                "percentage": analyzer.summary_stats()["critical_pct"]
            }
        },
        "articles_analyzed": list(analyzer.analyses.keys())
    }
    
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Generated: {summary_file.name}")
    generated_files.append(summary_file)

    # Show risk level definitions
    print("\n7. RISK LEVEL DEFINITIONS")
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
    print("\n8. GENERATED FILES")
    print("-" * 90)
    for file in sorted(output_dir.glob("*")):
        size = f"({file.stat().st_size:,} bytes)" if file.is_file() else ""
        print(f"  ✓ {file.name} {size}")
    print()

    print(f"✅ Analysis complete!")
    print(f"📊 All reports saved to: {output_dir.absolute()}")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
