# SBC (Sociedade Brasileira de Computação) Style

## Overview
SBC is the bibliography style used by the Brazilian Computer Society for papers and publications.

## Format Example
```
Silva, João and Costa, Maria. 2023. Title of the paper. In: Anais do XXIII CSBC, pages 1-10.
```

## Characteristics
- Author names: "Last, First" format
- Multiple authors separated by "and"
- Year appears after authors
- Venues often in Portuguese (Anais do...)
- Pages indicated with "pages" or "pp."
- Generally similar to ACL/Natbib format

## Key Pattern
```regex
^[A-Z][A-Za-z\s,.\-'&]+?\s+(?:and\s+)?[A-Z][a-z]+\.?\s+\d{4}
```

## Field Extraction Rules
1. **Authors**: Text before first comma or before year
2. **Year**: 4-digit number after author list
3. **Title**: Between year and "In:" section
4. **Venue**: After "In:" or "In Proceedings of"
5. **Pages**: After venue information

## Example References

### Journal Article
```
Pereira, Roberto and Oliveira, Ana. 2022. Machine learning applications in healthcare. 
In: Revista Brasileira de Informática, volume 15, pages 45-62.
```

### Conference Paper
```
Santos, Carlos and Lima, Patricia. 2023. Deep learning for natural language processing. 
In: Anais do XXIII Congresso da SBC, pages 100-115.
```

### Book Chapter
```
Costa, Maria Elena. 2021. Advanced topics in databases. 
In: Advances in Computer Science, chapter 5, pages 120-150.
```

## Relation to ACL Style
SBC is essentially the Brazilian adaptation of the ACL/Natbib bibliography style.
The main differences are:
- Often Portuguese venue names
- Similar field structure
- Same author-year format
