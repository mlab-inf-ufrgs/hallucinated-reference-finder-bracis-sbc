"""Example demonstrating multi-style bibliography support in hallucinated reference detection pipeline."""

from pathlib import Path
from src.halref.extract.field_parsers.style_detector import StyleDetector
from src.halref.extract.field_parsers.style_specific_parsers import (
    ACLFieldParser,
    SBCFieldParser,
    SPLNCSFieldParser,
)


def demonstrate_extraction_phase():
    """Show the extraction phase with style detection."""
    print("=" * 70)
    print("EXTRACTION PHASE: Multi-Style Bibliography Support")
    print("=" * 70)

    # Example references in different styles
    references = [
        "Smith, John and Jane Doe. 2023. A study on language models. In Proceedings of ACL, pages 1-10.",
        "Johnson, Robert. 2022. Deep learning approaches. In Advances in Neural Networks.",
        "[1] Wilson, M.: Neural network optimization. In: Proceedings of ICML (2021): pp. 100–115.",
        "[2] Lee, S. and Park, K.: Transfer learning survey. In: Journal of AI (2020): pp. 45–60.",
    ]

    print(f"\n📚 Detected {len(references)} references")

    # Detect style
    detected_style = StyleDetector.detect_style_from_batch(references)
    print(f"📍 Detected style: {detected_style.value.upper()}")

    # Parse with style-specific parsers
    print("\n🔍 Parsing results:")
    print("-" * 70)

    if detected_style.value == "acl":
        parser = ACLFieldParser()
    elif detected_style.value == "splncs":
        parser = SPLNCSFieldParser()
    else:
        parser = ACLFieldParser()

    for i, ref_text in enumerate(references, 1):
        ref = parser.parse(ref_text)
        print(f"\nRef {i}:")
        print(f"  Title: {ref.title}")
        print(f"  Authors: {[f'{a.last_name}, {a.first_name}' for a in (ref.authors or [])]}")
        print(f"  Year: {ref.year}")
        print(f"  Venue: {ref.venue}")


def demonstrate_verification_phase():
    """Explain what stays the same (unchanged)."""
    print("\n" + "=" * 70)
    print("VERIFICATION PHASE: UNCHANGED")
    print("=" * 70)

    print("""
The verification pipeline remains EXACTLY THE SAME:

1. 🔗 API Lookup (Crossref/DBLP)
   - Takes parsed reference fields (title, authors, year, venue)
   - Searches external APIs
   - UNCHANGED from original implementation

2. 🎯 Deduplication
   - Merges duplicate references
   - Uses author/title/year similarity
   - UNCHANGED

3. 📊 Scoring
   - Calculates hallucination signals
   - Scores each reference
   - UNCHANGED

4. ✅ Final Classification
   - Flags likely hallucinated references
   - UNCHANGED

The ONLY change is in the EXTRACTION LAYER:
- Now automatically detects bibliography style
- Uses appropriate parsers for that style
- Feeds parsed results to unchanged verification pipeline
    """)


def demonstrate_hallucination_signals():
    """Show that hallucination detection is independent of style."""
    print("\n" + "=" * 70)
    print("HALLUCINATION SIGNALS: Style-Independent")
    print("=" * 70)

    print("""
Hallucination indicators (all working with any style):

✗ No match in Crossref/DBLP
  - Reference cannot be found in major databases
  - Works with ACL, SBC, SPLNCS equally

✗ Citation count mismatch
  - Cited more/less than actual in system
  - Independent of bibliography style

✗ Venue/Journal anomalies
  - Venue doesn't exist for that year
  - Works with any format

✗ Author name inconsistencies
  - Different author names across citations
  - Detected after parsing (style-independent)

✗ Temporal inconsistencies
  - References to future events
  - Works with any style
    """)


def demonstrate_end_to_end():
    """Show complete flow."""
    print("\n" + "=" * 70)
    print("COMPLETE PIPELINE FLOW")
    print("=" * 70)

    print("""
INPUT: PDF document with mixed bibliography styles

↓ (EXTRACTION LAYER - CHANGED)

Step 1: Extract text from PDF
Step 2: Split into reference strings
Step 3: Detect bibliography style (ACL/SBC/SPLNCS)
Step 4: Select style-specific parser
Step 5: Parse references → Extract fields

↓ (VERIFICATION LAYER - UNCHANGED)

Step 6: API lookup (Crossref, DBLP)
Step 7: Deduplication
Step 8: Scoring (hallucination signals)
Step 9: Classification (hallucinated? yes/no)

OUTPUT: List of references with hallucination confidence
    """)


if __name__ == "__main__":
    demonstrate_extraction_phase()
    demonstrate_verification_phase()
    demonstrate_hallucination_signals()
    demonstrate_end_to_end()

    print("\n" + "=" * 70)
    print("✅ Multi-style bibliography support is transparent to verification layer!")
    print("=" * 70)
