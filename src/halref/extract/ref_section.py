"""Locate the bibliography block inside extracted PDF text (ACL, SBC, LNCS, Portuguese)."""

from __future__ import annotations

import re

# Standalone heading line — Brazilian / Springer templates often use these.
# pdfminer often emits TeX-style "Referˆencias" (U+02C6 modifier before "e") instead of "Referências".
REF_HEADING = re.compile(
    r"(?:^|\n)\s*(?:"
    r"References|REFERENCES|"
    r"Bibliography|BIBLIOGRAPHY|"
    r"Referências|REFERÊNCIAS|"
    r"Refer\u02c6encias|"
    r"Referências\s+Bibliográficas|REFERÊNCIAS\s+BIBLIOGRÁFICAS|"
    r"Bibliografia|BIBLIOGRAFIA"
    r")\s*\n",
    re.IGNORECASE,
)

# End of bibliography: appendix-like sections (EN + PT).
STOP_AFTER_REFERENCES = re.compile(
    r"\n\s*(?:"
    r"Appendix|Appendices|Apêndice|Apêndices|Apendice|Apendices|"
    r"Anexo|Anexos|"
    r"Supplementary|Supplemental|Checklist|"
    r"[A-H]\s+[A-Z][a-z]"
    r"|\d+\s+(?:Appendix|Supplementary|Additional)"
    r"|[A-H]\.\d+\s+[A-Z]"
    r"|Acknowledgment|Acknowledgement|Agradecimentos"
    r"|Ethics\s+Statement|Limitations"
    r"|Broader\s+Impact|Impact\s+Statement"
    r"|Additional\s+(?:Experiments|Details|Results|Analysis|Examples)"
    r"|Supplementary\s+Material"
    r"|Reproducibility"
    r"|(?:Figure|Table)\s+\d+\s*:"
    r"|Prompt\s+Template|Evaluation\s+(?:Form|Rubric|Criteria)"
    r"|Implementation\s+Details|Hyperparameter"
    r"|Dataset\s+(?:Details|Statistics|Description)"
    r")\b",
    re.IGNORECASE,
)


def slice_reference_body(text: str) -> str:
    """Return only the text after the bibliography heading, truncated before appendix etc."""
    match = REF_HEADING.search(text)
    if not match:
        return text.strip()
    after = text[match.end() :]
    stop = STOP_AFTER_REFERENCES.search(after)
    if stop:
        after = after[: stop.start()]
    return after.strip()
