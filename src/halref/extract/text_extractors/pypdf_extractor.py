"""pypdf-based text extraction — good quality, already installed."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from halref.extract.base import TextExtractor
from halref.extract.ref_section import REF_HEADING, slice_reference_body

logger = logging.getLogger(__name__)


class PypdfExtractor(TextExtractor):
    """Extract text using pypdf.

    Good word spacing and two-column handling.
    Does not insert blank lines between references (unlike pdfminer).
    """

    name = "pypdf"

    def extract_text(
        self, pdf_path: Path, page_range: tuple[int, int] | None = None
    ) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))

        if page_range:
            start, end = page_range
            pages = range(start, min(end, len(reader.pages)))
            texts = [reader.pages[i].extract_text() or "" for i in pages]
        else:
            texts = self._extract_auto(reader)

        full_text = "\n\n".join(texts)
        full_text = self._strip_line_numbers(full_text)
        return slice_reference_body(full_text)

    def _extract_auto(self, reader) -> list[str]:
        """Scan pages backwards to find References, extract from there."""
        total = len(reader.pages)
        ref_page = None

        for i in range(total - 1, -1, -1):
            text = reader.pages[i].extract_text() or ""
            text = self._strip_line_numbers(text)
            if REF_HEADING.search(text):
                ref_page = i
                break

        if ref_page is None:
            logger.warning("No References heading found")
            start = max(0, total - 3)
            return [reader.pages[i].extract_text() or "" for i in range(start, total)]

        # Extract all remaining pages; _find_references_section() stops at appendix
        return [reader.pages[i].extract_text() or "" for i in range(ref_page, total)]

    @staticmethod
    def _strip_line_numbers(text: str) -> str:
        """Remove line numbers from ACL review-mode PDFs."""
        lines = text.split("\n")
        filtered = [line for line in lines if not re.match(r"^\s*\d{1,4}\s*$", line)]
        return "\n".join(filtered)
