"""Docling-based text extraction with layout-aware section detection."""

from __future__ import annotations

import os
from pathlib import Path

from halref.extract.base import TextExtractor


class DoclingExtractor(TextExtractor):
    name = "docling"

    def is_available(self) -> bool:
        try:
            import docling  # noqa: F401
            return True
        except ImportError:
            return False

    def extract_text(
        self, pdf_path: Path, page_range: tuple[int, int] | None = None
    ) -> str:
        from docling.document_converter import DocumentConverter

        converter = self._make_converter()
        result = converter.convert(str(pdf_path))
        doc = result.document

        # Try to find the references section from the structured document
        ref_text = self._find_references_section(doc)

        if not ref_text and page_range:
            # Fall back to full markdown and extract from expected location
            full_md = doc.export_to_markdown()
            ref_text = self._extract_from_markdown(full_md)

        return ref_text or ""

    @staticmethod
    def _make_converter():
        """Prefer GPU (CUDA/MPS) when ``DOCLING_DEVICE`` / torch say so; else CPU."""
        try:
            from docling.datamodel.accelerator_options import (
                AcceleratorDevice,
                AcceleratorOptions,
            )
            from docling.document_converter import DocumentConverter

            raw = (os.environ.get("DOCLING_DEVICE") or "").lower()
            if raw == "cpu":
                dev = AcceleratorDevice.CPU
            elif raw == "mps":
                dev = AcceleratorDevice.MPS
            elif raw.startswith("cuda"):
                dev = AcceleratorDevice.CUDA
            else:
                dev = AcceleratorDevice.AUTO
            return DocumentConverter(
                accelerator_options=AcceleratorOptions(device=dev),
            )
        except Exception:
            from docling.document_converter import DocumentConverter

            return DocumentConverter()

    def _find_references_section(self, doc) -> str:
        """Extract references section from Docling's structured document."""
        md = doc.export_to_markdown()
        return self._extract_from_markdown(md)

    def _extract_from_markdown(self, md: str) -> str:
        """Find references section in markdown output."""
        import re

        # Look for References heading in markdown
        pattern = re.compile(
            r"^#{1,3}\s*(?:References|Bibliography|Works Cited)\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(md)
        if not match:
            return ""

        text_after = md[match.end():].strip()

        # Stop at next major heading
        next_heading = re.search(r"^#{1,2}\s+\w", text_after, re.MULTILINE)
        if next_heading:
            text_after = text_after[:next_heading.start()].strip()

        return text_after
