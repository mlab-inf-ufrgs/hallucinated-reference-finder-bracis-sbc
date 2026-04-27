# New Bibliography Styles Documentation

This folder contains documentation for the two new bibliography styles that have been integrated into the hallucinated reference detection system.

## Styles Included

### 1. SBC (Sociedade Brasileira de Computação)
- **File**: [SBC_STYLE.md](SBC_STYLE.md)
- **Purpose**: Brazilian Computer Society style for academic publications
- **Format**: Similar to ACL/Natbib with Portuguese venue names
- **Key Feature**: Author-year format with "In:" venue marker

### 2. SPLNCS (Springer Lecture Notes in Computer Science)
- **File**: [SPLNCS_STYLE.md](SPLNCS_STYLE.md)
- **Purpose**: Springer's numbered reference format for LNCS series
- **Format**: [N] Author, I.: Title. In: Venue (YYYY): pp. X–Y.
- **Key Feature**: Numbered references with compact author format

## Integration

Both styles are now fully integrated into the hallucinated reference detection pipeline:

### Style Detection
The system automatically detects which style is used in a document by analyzing reference patterns.

### Style-Specific Parsing
Each style has a dedicated parser that correctly extracts:
- Authors
- Title
- Year
- Venue
- Pages (when present)
- DOI (when present)
- URL (when present)

### Verification Pipeline (Unchanged)
After parsing, references feed into the unchanged verification pipeline:
1. API lookup (Crossref, DBLP, Semantic Scholar)
2. Deduplication
3. Hallucination signal scoring
4. Classification (hallucinated or not)

## Reference Examples

### SBC Format
```
Silva, João and Costa, Maria. 2023. Title of the paper. In: Anais do XXIII CSBC, pages 1-10.
```

### SPLNCS Format
```
[1] Smith, J. and Doe, J.: A comprehensive study. In: Proceedings of Conference (2023): pp. 100–115.
```

## Testing

All styles have been tested with real examples:
- ✅ SBC parsing verified
- ✅ SPLNCS parsing verified
- ✅ Auto-detection confirmed
- ✅ Integration with pipeline validated

Test file: `tests/test_style_detection.py` (4 passing tests)

## Code References

### Style Detector
- **File**: `src/halref/extract/field_parsers/style_detector.py`
- **Class**: `StyleDetector`
- **Key Method**: `detect_style_from_batch(references)`

### Style-Specific Parsers
- **File**: `src/halref/extract/field_parsers/style_specific_parsers.py`
- **Classes**: `SBCFieldParser`, `SPLNCSFieldParser`
- **Usage**: Automatically selected by `ensemble.py` based on detected style

### Pipeline Integration
- **File**: `src/halref/extract/ensemble.py`
- **Functions**: 
  - `get_style_specific_parsers(style)`
  - `_detect_reference_style(references)`
- **Impact**: Transparent to verification pipeline

## Extending to More Styles

To add support for another bibliography style:

1. Create documentation in `new-styles/YOUR_STYLE.md`
2. Add enum value to `ReferenceStyle` in `style_detector.py`
3. Add detection pattern to `StyleDetector` class
4. Create parser class extending `FieldParser` in `style_specific_parsers.py`
5. Register in `get_style_specific_parsers()`
6. Add tests in `tests/test_style_detection.py`

See `ADAPTATION_NOTES.md` for detailed extension guide.
