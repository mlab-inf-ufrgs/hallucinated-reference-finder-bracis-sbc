# halref — Hallucinated Reference Finder

**🔄 BRACIS/SBC Adaptation — Detect AI-Generated Citations in Academic Papers**

This is an adaptation of the original [Hallucinated Reference Finder](https://github.com/davidjurgens/hallucinated-reference-finder) for **Brazilian academic papers** with **SBC** and **BRACIS** bibliography styles.

Detects hallucinated (AI-generated) references in PDF papers by:
1. **Extracting** citations from PDFs locally
2. **Parsing** authors, titles, years, and venues  
3. **Verifying** against Semantic Scholar and OpenAlex APIs
4. **Scoring** hallucination likelihood based on 5 factors
5. **Reporting** flagged references with side-by-side comparison

## Features

✅ **Supports Brazilian Styles**
- **SBC**: Natbib format (Last, First and First Last)
- **BRACIS**: Numbered format ([N] Last, I.: Title...)

✅ **Free APIs** (No subscription needed)
- Semantic Scholar
- OpenAlex

✅ **Rich Output**
- Terminal tables with risk colors and percentages
- BibTeX bibliography with hallucination metadata
- JSON verification reports
- Risk analysis table by article

## Quick Start

### Install (Python 3.11+)

```bash
# Activate virtual environment
source .venv/bin/activate

# Install
pip install -e .
```

### Usage

```bash
# Extract references (offline, no API calls)
python -m halref.cli extract paper.pdf -d output/

# Check for hallucinated references
python -m halref.cli check paper.pdf -d results/

# Check directory of PDFs
python -m halref.cli check submissions/ -d results/

# Show all references (not just flagged)
python -m halref.cli check paper.pdf --show-ok

# Demo with test data
python analysis_example.py
```

## Example Output

### Terminal Report
```
┏━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃   # ┃ Score ┃ Extracted      ┃ Database     ┃ Difference┃
┡━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━┩
│  1  │ 0.12  │ Smith et al.   │ Smith et al. │ ✓ Match   │
│  2  │ 0.84  │ WHO (2025)     │ Halpin (2022)│ ✗ Year    │
└─────┴───────┴────────────────┴──────────────┴───────────┘
```

### Risk Analysis Table
```
Article ID    Very Low  Low       Medium    High      Critical  Total
────────────────────────────────────────────────────────────────────
article_001   1(12.5%)  2(25.0%)  2(25.0%)  1(12.5%)  2(25.0%)  8
article_002   1(16.7%)  2(33.3%)  1(16.7%)  1(16.7%)  1(16.7%)  6
```

## How It Works

### Phase 1: Extraction (Offline, ~0.2s)
- Detects reference style (SBC/BRACIS)
- Extracts title, authors, year, venue
- Parses author names
- Validates completeness

### Phase 2: Verification (API calls, 30-60s per 20 refs)
- Queries Semantic Scholar API
- Queries OpenAlex API
- Fuzzy-matches titles
- Checks author overlap
- Verifies publication year

### Phase 3: Scoring (Instant, ~100ms)
Composite score (0.0 = real, 1.0 = hallucinated):
- **Title match** (30%) — Similarity of extracted vs. database title
- **Authors** (25%) — Are the authors in the database paper?
- **Author order** (15%) — Correct author order?
- **Year** (15%) — Correct publication year?
- **Consensus** (15%) — Found in multiple databases?

## Risk Levels

| Level | Score | Meaning |
|-------|-------|---------|
| **Very Low** | 0.0-0.2 | Verified in multiple databases |
| **Low** | 0.2-0.4 | Found with minor differences |
| **Medium** | 0.4-0.6 | Found with notable differences |
| **High** | 0.6-0.8 | Not found or major disagreement |
| **Critical** | 0.8-1.0 | Likely AI-generated (hallucinated) |

## Installation

### Core Dependencies
```bash
pip install -e .
```

### With Optional Backends
```bash
# All extras
pip install -e ".[all]"

# Specific extras
pip install -e ".[docling]"     # Better PDF parsing
pip install -e ".[marker]"      # ML-based extraction
pip install -e ".[llm]"         # LLM verification
pip install -e ".[acl]"         # ACL Anthology lookup
```

## Configuration

Create `config.toml` to customize (or use `config.example.toml` as template):

```toml
[extraction]
confidence_threshold = 0.5      # Min extraction confidence

[matching]
title_weight = 0.30             # Title matching weight
author_weight = 0.25            # Author matching weight
year_threshold = 2              # Allow ±N years difference

[verification]
threshold = 0.5                 # Flag if score >= threshold
show_ok = false                 # Show all (not just flagged)

[apis.semantic_scholar]
api_key = ""
enabled = true

[apis.openalex]
api_key = ""
enabled = true
```

## Project Structure

```
src/halref/
├── extract/              # PDF parsing & reference extraction
│   └── field_parsers/    # SBC, BRACIS format parsers
├── matching/             # Verification and scoring
├── apis/                 # API integrations (Semantic Scholar, OpenAlex)
├── output/               # BibTeX, JSON, report generation
├── analysis.py           # Hallucination analysis & tables
├── cli.py                # Command-line interface
└── models.py             # Data structures

new-styles/
├── sbc.bst               # SBC bibliography style
└── splncs04.bst          # BRACIS bibliography style (numbered format)
```

## Differences from Original

| Aspect | Original | This Version |
|--------|----------|--------------|
| **Styles** | ACL, SBC, SPLNCS | SBC, BRACIS |
| **Language** | English/General | Portuguese/Brazilian |
| **APIs** | Multiple | Semantic Scholar, OpenAlex |
| **Analysis** | Basic report | Risk analysis table by article |
| **Target** | General CS | Brazilian conferences |

## API Rate Limits

Free tier (no subscription):
- **Semantic Scholar**: ~100 requests/5 minutes
- **OpenAlex**: ~10 requests/second

Expected time: ~4-5 minutes per 20 references

For faster verification, get free API keys:
- Semantic Scholar: https://www.semanticscholar.org/product/api#api-key
- OpenAlex: https://openalex.org/settings/api-key

## Testing

```bash
# Demo with synthetic data
python analysis_example.py

# Full test with real PDF
pip install -e .
python test_hallucination_detection.py
```

Expected output:
```
✓ Extraction: 20 references
✓ Verification: 18 verified (4-5 minutes with APIs)
✓ Scoring: Risk analysis table with percentages
✓ Summary: Total hallucination statistics
```

## Example: Multi-Article Analysis

```python
from pathlib import Path
from halref.analysis import HallucinationAnalyzer
from halref.pipeline import run_check
from halref.config import Config
import asyncio

# Process multiple PDFs
config = Config.default()
pdf_dir = Path("papers/")
batch_report = asyncio.run(run_check(list(pdf_dir.glob("*.pdf")), config))

# Analyze
analyzer = HallucinationAnalyzer()
analyzer.analyze_batch_report(batch_report, id_prefix="Paper")

# Display results
analyzer.print_table()
analyzer.print_summary()
```

## Library Usage

```python
from pathlib import Path
from halref.extract.ensemble import extract_references
from halref.config import Config

# Extract only (offline)
config = Config.default()
refs = extract_references(Path("paper.pdf"), config)
for ref in refs:
    print(f"{ref.authors[0]} ({ref.year}). {ref.title}")
```

## Privacy

✅ **Fully offline extraction** — No PDF content is sent anywhere  
⚠️ **Verification sends metadata** — Only reference metadata (title, authors, year) is sent to APIs  
✅ **No permanent logs** — Results stay on your machine

## Troubleshooting

### PDF Extraction Issues
- Try different extractors: pdfminer → pypdf → pdfplumber
- Use `--show-ok` to see what was extracted
- Check if PDF is text-based (not scanned image)

### Missing References
- Verify formatting matches SBC/BRACIS style
- Use `--debug` for detailed logs

### API Timeout
- Check internet connection
- Retry after a few minutes (rate limit)
- Verify API keys in config.toml

## License

MIT License. See LICENSE file.

Original project: [davidjurgens/hallucinated-reference-finder](https://github.com/davidjurgens/hallucinated-reference-finder)

---

**Questions?** Run `python analysis_example.py` to see a working demo.
