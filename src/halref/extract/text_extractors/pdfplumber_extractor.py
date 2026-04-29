"""pdfplumber-based text extraction with targeted page support."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pdfplumber

from halref.extract.base import TextExtractor
from halref.extract.ref_section import REF_HEADING, slice_reference_body

logger = logging.getLogger(__name__)


class PdfplumberExtractor(TextExtractor):
    name = "pdfplumber"

    def extract_text(
        self, pdf_path: Path, page_range: tuple[int, int] | None = None
    ) -> str:
        if page_range:
            return self._extract_pages(pdf_path, page_range)
        return self._extract_auto(pdf_path)

    def _extract_pages(self, pdf_path: Path, page_range: tuple[int, int]) -> str:
        """Extract text from specific pages (0-indexed).

        When a page range is specified, the user has indicated these pages
        contain references. We extract all text and try to find the References
        heading. If found, we return text after it. If not (e.g., references
        span multiple pages and the heading is only on the first), we return
        all extracted text, trusting the user's page range.
        """
        start, end = page_range
        pages_idx = list(range(start, end))
        all_page_texts = []
        with pdfplumber.open(pdf_path, pages=pages_idx) as pdf:
            for page in pdf.pages:
                text = self._extract_page_columns(page)
                if text:
                    all_page_texts.append(text)

        combined = "\n\n".join(all_page_texts)
        combined = self._strip_line_numbers(combined)
        return slice_reference_body(combined)

    def _looks_like_references(self, text: str) -> bool:
        """Heuristic: does this text look like it's mostly references?"""
        years = re.findall(r"\b(?:19|20)\d{2}\b", text)
        years += re.findall(r"\((?:19|20)\d{2}\)", text)
        return len(years) >= 3

    @staticmethod
    def _strip_line_numbers(text: str) -> str:
        """Remove line-number-only lines (review-mode PDFs)."""
        lines = text.split("\n")
        filtered = [line for line in lines if not re.match(r"^\s*\d{1,4}\s*$", line)]
        return "\n".join(filtered)

    def _extract_page_columns(self, page) -> str:
        """Extract text from a page, handling two-column layout.

        Splits the page at the midpoint and reads left column then right column.
        """
        width = page.width
        height = page.height
        mid = width / 2

        # Try column-based extraction
        left_bbox = (0, 0, mid, height)
        right_bbox = (mid, 0, width, height)

        left_crop = page.crop(left_bbox)
        right_crop = page.crop(right_bbox)

        left_text = left_crop.extract_text() or ""
        right_text = right_crop.extract_text() or ""

        # Combine: left column first, then right column
        return left_text + "\n\n" + right_text

    def _extract_auto(self, pdf_path: Path) -> str:
        """Scan backwards from the last page for a bibliography heading (same idea as pdfminer)."""
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            ref_page: int | None = None
            for i in range(total - 1, -1, -1):
                text = self._extract_page_columns(pdf.pages[i])
                text = self._strip_line_numbers(text)
                if text and REF_HEADING.search(text):
                    ref_page = i
                    break

            if ref_page is None:
                logger.warning("No References/Referências heading found (pdfplumber)")
                start = max(0, total - 3)
                parts: list[str] = []
                for j in range(start, total):
                    t = self._extract_page_columns(pdf.pages[j])
                    if t:
                        parts.append(t)
                combined = "\n\n".join(parts)
                return slice_reference_body(self._strip_line_numbers(combined))

            parts = []
            for j in range(ref_page, total):
                t = self._extract_page_columns(pdf.pages[j])
                if t:
                    parts.append(t)
            combined = "\n\n".join(parts)
            return slice_reference_body(self._strip_line_numbers(combined))

    def _extract_refs_from_text(self, text: str) -> str:
        """If the text contains a bibliography heading, return only the body after it."""
        return slice_reference_body(text)
