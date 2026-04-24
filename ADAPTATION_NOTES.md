# Multi-Style Bibliography Support Adaptation

## Objective
Adapt the hallucinated reference detection pipeline to support multiple bibliography styles (ACL, SBC, SPLNCS) while maintaining the integrity of the hallucination detection verification pipeline.

**Key Principle**: The goal is NOT to detect which bibliography style is used. The goal is to support PARSING references in multiple styles so the verification pipeline can detect hallucinations accurately regardless of which style the document uses.

## Summary of Changes

### Files Created

1. **`src/halref/extract/field_parsers/style_detector.py`** (4.1 KB)
   - `ReferenceStyle` enum: ACL, SBC, SPLNCS, UNKNOWN
   - `StyleDetector` class: Pattern-based style detection
   - Auto-detects dominant bibliography style from reference batch

2. **`src/halref/extract/field_parsers/style_specific_parsers.py`** (14 KB)
   - `NatbibFieldParser`: Base class for ACL/SBC formats
   - `ACLFieldParser`: ACL-specific parsing
   - `SBCFieldParser`: SBC-specific parsing
   - `SPLNCSFieldParser`: SPLNCS-specific parsing

3. **`tests/test_style_detection.py`**
   - Test suite: 4 passing tests
   - Covers style detection, ACL/SPLNCS parsing, batch detection

4. **`example_pipeline.py`**
   - Demonstration of complete pipeline
   - Shows extraction + unchanged verification phases

### Files Modified

1. **`src/halref/extract/ensemble.py`**
   - Added `get_style_specific_parsers(style)` function
   - Added `_detect_reference_style(references)` function
   - Modified `extract_references()` to detect style and use appropriate parsers
   - Lines changed: ~30 new lines for integration

2. **`src/halref/extract/field_parsers/regex_parser.py`**
   - Updated class docstring to note backward compatibility
   - No functional changes

## Pipeline Architecture

### Extraction Layer (CHANGED)
```
PDF Text → Split References → Detect Style → Style-Specific Parsers → Parsed Fields
```

### Verification Layer (UNCHANGED)
```
Parsed Fields → API Lookup → Deduplication → Scoring → Classification
```

The detection of hallucinations happens entirely in the verification layer, which receives parsed fields from any style.

## Bibliography Style Patterns

### ACL (Association for Computational Linguistics)
```
Smith, John and Jane Doe. 2023. Title of paper. In Proceedings of ACL, pages 1-10.
```
- Pattern: "Author, Author. YYYY. Title. In Venue..."
- Natbib format with year after authors
- Detected by: Comma after author, year before title

### SBC (Sociedade Brasileira de Computação)
```
Silva, João. 2023. Título do artigo. In: Anais do XXIII CSBC, páginas 1-10.
```
- Similar to ACL (natbib format)
- May have Portuguese terminology
- Detected by: Comma after author, year pattern

### SPLNCS (Springer Lecture Notes in Computer Science)
```
[1] Smith, J.: Title of paper. In: Proceedings of ICML (2023): pp. 1–10.
```
- Numbered format with [N] prefix
- Author initials separated by commas
- Detected by: `[N]` at start and `(YYYY)` for year

## Implementation Details

### Style Detection Algorithm
```python
StyleDetector.detect_style_from_batch(references) -> ReferenceStyle
```
- Scores each reference against known patterns
- Returns dominant style
- Falls back to UNKNOWN if no clear pattern

### Parser Selection
```python
get_style_specific_parsers(style) -> list[FieldParser]
```
- Returns parser appropriate for detected style
- ACL → ACLFieldParser
- SBC → SBCFieldParser
- SPLNCS → SPLNCSFieldParser

### Field Extraction
Each style-specific parser extracts:
- `title`: Paper/article title
- `authors`: List of authors (normalized)
- `year`: Publication year
- `venue`: Conference/journal name
- `doi`: DOI if present
- `url`: URL if present

## Testing

Run style detection tests:
```bash
cd /home/renandrades/hallucinated-reference-finder/hallucinated-reference-finder-bracis
pytest tests/test_style_detection.py -v
```

All 4 tests passing:
- ✅ `test_style_detection`: Batch style detection
- ✅ `test_acl_parsing`: ACL format parsing
- ✅ `test_splncs_parsing`: SPLNCS format parsing
- ✅ `test_batch_detection`: Mixed style batches

## Backward Compatibility

- `regex_parser.py` remains unchanged functionally
- Still exported as "regex" parser
- Now works as an alias for ACLFieldParser
- Existing code using `RegexFieldParser` continues to work

## Verification Pipeline (UNCHANGED)

The core hallucination detection system is completely unchanged:

1. **API Search**: Uses Crossref and DBLP APIs
   - Takes parsed fields (title, authors, year)
   - Works with any style's output

2. **Deduplication**: Merges near-duplicate references
   - Uses author/title/year similarity
   - Style-independent logic

3. **Scoring**: Calculates hallucination signals
   - No match in database: Hallucinated
   - Citation count mismatch: Suspicious
   - Temporal inconsistencies: Hallucinated
   - Author name anomalies: Hallucinated
   - All signals work with any style

4. **Final Classification**: Flags hallucinated references
   - Same confidence scoring
   - Same output format

## Extension Guide

To add support for another bibliography style:

1. **Create style enum** in `style_detector.py`:
   ```python
   class ReferenceStyle(Enum):
       NEW_STYLE = "new_style"
   ```

2. **Add detection pattern** in `StyleDetector`:
   ```python
   NEW_STYLE_PATTERN = r"pattern_here"
   ```

3. **Create parser class** in `style_specific_parsers.py`:
   ```python
   class NewStyleFieldParser(FieldParser):
       name = "new_style"
       def parse(self, raw_text: str) -> Reference:
           # Implementation
   ```

4. **Register in `get_style_specific_parsers()`**:
   ```python
   elif style == "new_style":
       return [NewStyleFieldParser()]
   ```

5. **Add tests** in `tests/test_style_detection.py`

## Files Structure

```
src/halref/
├── extract/
│   ├── ensemble.py (MODIFIED)
│   └── field_parsers/
│       ├── regex_parser.py (MODIFIED - backward compat)
│       ├── style_detector.py (NEW)
│       └── style_specific_parsers.py (NEW)
tests/
├── test_style_detection.py (NEW)
example_pipeline.py (NEW)
ADAPTATION_NOTES.md (NEW - this file)
```

## Summary

- ✅ **Multi-style support**: ACL, SBC, SPLNCS fully supported
- ✅ **Auto-detection**: Style detected automatically from references
- ✅ **Backward compatible**: Existing code unchanged
- ✅ **Zero impact on verification**: Hallucination detection unchanged
- ✅ **Tested**: 4 passing test cases
- ✅ **Documented**: Complete pipeline documentation
- ✅ **Extensible**: Easy to add new styles
