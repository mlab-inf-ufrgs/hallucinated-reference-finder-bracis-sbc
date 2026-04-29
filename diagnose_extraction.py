#!/usr/bin/env python3
"""Diagnostic script to analyze reference extraction from PDFs."""

from pathlib import Path
import json
from halref.config import load_config
from halref.extract.ensemble import extract_references, get_text_extractors

def diagnose_pdf(pdf_path: Path) -> dict:
    """Analyze reference extraction for a single PDF."""
    config = load_config(None)
    
    print(f"\n{'='*80}")
    print(f"Analyzing: {pdf_path.name}")
    print(f"{'='*80}\n")
    
    # Try different text extractors
    extractors = get_text_extractors(config)
    
    results = {
        "pdf": pdf_path.name,
        "extractors": {}
    }
    
    for extractor in extractors:
        print(f"\n📄 Extractor: {extractor.name.upper()}")
        print("-" * 80)
        
        try:
            text = extractor.extract_text(pdf_path)
            
            # Show first 500 chars
            preview = text[:500].replace('\n', '\\n')
            print(f"Text preview (first 500 chars):\n{preview}...\n")
            print(f"Total text length: {len(text)} chars")
            print(f"Number of lines: {len(text.split(chr(10)))}")
            
            # Try to split references
            from halref.extract.splitter import split_references
            refs = split_references(text)
            
            print(f"\n✓ Found {len(refs)} reference blocks")
            
            if len(refs) <= 10:
                print("\nReference blocks:")
                for i, ref in enumerate(refs, 1):
                    preview = ref[:100].replace('\n', ' ')
                    print(f"  [{i}] {preview}..." if len(ref) > 100 else f"  [{i}] {preview}")
            else:
                print("\nFirst 5 references:")
                for i, ref in enumerate(refs[:5], 1):
                    preview = ref[:100].replace('\n', ' ')
                    print(f"  [{i}] {preview}..." if len(ref) > 100 else f"  [{i}] {preview}")
                print(f"  ... ({len(refs) - 5} more references)")
            
            results["extractors"][extractor.name] = {
                "text_length": len(text),
                "num_lines": len(text.split('\n')),
                "num_refs_found": len(refs),
                "refs_preview": [r[:100] for r in refs[:3]]
            }
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            results["extractors"][extractor.name] = {"error": str(e)}
    
    # Try ensemble extraction
    print(f"\n📊 ENSEMBLE EXTRACTION")
    print("-" * 80)
    
    try:
        refs = extract_references(pdf_path, config)
        print(f"✓ Ensemble found {len(refs)} references")
        
        if len(refs) <= 10:
            print("\nExtracted references:")
            for i, ref in enumerate(refs, 1):
                print(f"  [{i}] {ref.title[:60]}..." if ref.title and len(ref.title) > 60 else f"  [{i}] {ref.title or 'NO TITLE'}")
        else:
            print("\nFirst 5 extracted references:")
            for i, ref in enumerate(refs[:5], 1):
                print(f"  [{i}] {ref.title[:60]}..." if ref.title and len(ref.title) > 60 else f"  [{i}] {ref.title or 'NO TITLE'}")
            print(f"  ... ({len(refs) - 5} more references)")
        
        results["ensemble"] = {
            "total_refs": len(refs),
            "refs": [
                {
                    "title": r.title or "",
                    "authors": [str(a) for a in (r.authors or [])],
                    "year": r.year,
                    "venue": r.venue or ""
                }
                for r in refs
            ]
        }
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        results["ensemble"] = {"error": str(e)}
    
    return results


def main():
    """Run diagnostics on all test PDFs."""
    pdf_folder = Path("pdf-inputs")
    pdf_files = sorted(pdf_folder.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in pdf-inputs/")
        return
    
    print("\n" + "="*80)
    print("REFERENCE EXTRACTION DIAGNOSTIC")
    print("="*80)
    print(f"\nFound {len(pdf_files)} PDF files\n")
    
    all_results = {}
    for pdf_path in pdf_files:
        result = diagnose_pdf(pdf_path)
        all_results[pdf_path.name] = result
    
    # Summary
    print("\n\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    summary = {
        "total_pdfs": len(pdf_files),
        "pdfs": {}
    }
    
    for pdf_name, data in all_results.items():
        num_refs = data.get("ensemble", {}).get("total_refs", 0)
        summary["pdfs"][pdf_name] = {
            "num_references": num_refs
        }
        print(f"\n{pdf_name}: {num_refs} references")
        
        if "ensemble" in data and "refs" in data["ensemble"]:
            refs = data["ensemble"]["refs"]
            for i, ref in enumerate(refs, 1):
                title = ref["title"][:50] + "..." if len(ref["title"]) > 50 else ref["title"]
                year = ref["year"] or "?"
                print(f"  [{i:2d}] {year} - {title}")
    
    # Save results
    output_file = Path("extraction_diagnostic.json")
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Diagnostic saved to: {output_file}")


if __name__ == "__main__":
    main()
