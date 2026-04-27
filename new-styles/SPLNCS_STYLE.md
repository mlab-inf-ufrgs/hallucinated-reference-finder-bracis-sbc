# SPLNCS (Springer Lecture Notes in Computer Science) Style

## Overview
SPLNCS is the bibliography style used by Springer for the Lecture Notes in Computer Science (LNCS) series, widely used in computer science conferences.

## Format Example
```
[1] Smith, J. and Doe, J.: A comprehensive study on machine learning. In: Proceedings 
of the 25th International Conference (2023): pp. 100–115.
```

## Characteristics
- References numbered with [N] at the beginning
- Author names in "Last, Initial" or "Last, First" format
- Multiple authors separated by "and"
- Colon ":" after author list
- Year in parentheses: (YYYY)
- Pages indicated with "pp." or "pages"
- "In:" marks the venue section
- Title between author colon and "In:"

## Key Patterns
```regex
^\s*\[\d+\]                          # Numbered reference [1], [2], etc.
\((\d{4})\)                          # Year in parentheses
Last, Initial\.:                     # Author format
```

## Field Extraction Rules
1. **Reference Number**: `[N]` at the start
2. **Authors**: Between start and first `:`, in "Last, Initial" format
3. **Title**: Between first `:` and "In:"
4. **Venue**: After "In:" and before year in parentheses
5. **Year**: Inside parentheses `(YYYY)`
6. **Pages**: After year, usually in format "pp. X–Y"

## Example References

### Conference Paper
```
[1] Johnson, M. and Smith, P.: Advances in neural network optimization. In: Proceedings 
of the International Conference on Learning Representations (2023): pp. 1–18.
```

### Journal Article
```
[2] Williams, A.: A survey on deep learning approaches in NLP. In: IEEE Transactions 
on Pattern Analysis and Machine Intelligence, vol. 45 (2022): pp. 234–256.
```

### Workshop Paper
```
[3] Davis, R. and Brown, K. and Green, J.: Benchmarking transformer models. In: Proceedings 
of the 10th Workshop on Neural Machine Translation (2023): pp. 45–60.
```

### Book Chapter
```
[4] Anderson, T.: Formal language theory. In: Handbook of Theoretical Computer Science, 
Part B, chapter 5 (1990): pp. 245–305.
```

## Style Details

### Author Format
- Typically: "Last, Initial." for single author
- Multiple: "Last, Initial. and Last, Initial. and Last, Initial."
- Sometimes extended to "Last, First" or "Last, F."

### Venue Information
- Conference: "Proceedings of [Conference Name]"
- Journal: "[Journal Name], volume X"
- Book: "[Book Title], chapter X"

### Punctuation
- Colon after authors: `:`
- "In:" before venue (lowercase 'n')
- Year in parentheses: `(YYYY)`
- Pages with em-dash: `pp. 100–115`

## Comparison with Other Styles
- More structured than ACL (numbered format)
- More concise author format than ACL (initials vs. full first names)
- Similar venue information to ACL
- Unique numbered format makes detection easier
