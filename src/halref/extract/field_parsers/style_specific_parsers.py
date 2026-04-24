"""Style-specific field parsers for different bibliography formats."""

from __future__ import annotations

import re

from nameparser import HumanName

from halref.extract.base import FieldParser
from halref.models import Author, Reference


class NatbibFieldParser(FieldParser):
    """Base parser for natbib-style references (ACL and SBC).

    Expected format for ACL/SBC:
        Last, First and First Last. Year. Title. In Venue, pages X-Y.
    """

    name = "natbib"

    YEAR_PATTERN = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")
    VENUE_PATTERN = re.compile(
        r"\b[Ii]n\s+"
        r"(Proceedings\s+of\s+.*?"
        r"|Advances\s+in\s+.*?"
        r"|Transactions\s+of\s+.*?"
        r"|(?:the\s+)?(?:\d+(?:st|nd|rd|th)\s+)?"
        r"[A-Z].*?)"
        r"(?:\.\s*$|,\s*pages\b|,\s*pp\b|\.$)",
        re.DOTALL,
    )
    DOI_PATTERN = re.compile(r"\b(10\.\d{4,}/[^\s]+)")
    URL_PATTERN = re.compile(r"(https?://[^\s]+)")

    def parse(self, raw_text: str) -> Reference:
        """Parse a natbib-style reference."""
        text = raw_text.strip()

        # Strip leading [N] reference numbers
        text = re.sub(r"^\s*\[\d+\]\s*", "", text)

        ref = Reference(raw_text=raw_text)

        # Extract year
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            ref.year = int(year_match.group(1))

        # Extract venue (from "In ..." section)
        venue_match = self.VENUE_PATTERN.search(text)
        if venue_match:
            ref.venue = venue_match.group(1).strip()

        # Extract DOI
        doi_match = self.DOI_PATTERN.search(text)
        if doi_match:
            ref.doi = doi_match.group(1)

        # Extract URL
        url_match = self.URL_PATTERN.search(text)
        if url_match:
            ref.url = url_match.group(1)

        # Extract title (between year and "In" or end)
        title_start = text.find(". ") + 2 if ". " in text else 0
        if year_match:
            title_start = year_match.end()
            if text[title_start:title_start + 2] == ". ":
                title_start += 2

        title_end = text.find(" In ", title_start) if " In " in text[title_start:] else len(text)
        if title_end == -1:
            title_end = len(text)

        if title_start < title_end:
            title = text[title_start:title_end].strip()
            title = re.sub(r"^[\.\s]+", "", title)
            ref.title = title

        # Extract authors (from start to first year)
        if year_match:
            author_text = text[:year_match.start()].strip()
            ref.authors = self._parse_authors(author_text)

        return ref

    def _parse_authors(self, author_text: str) -> list[Author]:
        """Parse authors from text like 'Last, First and Last, First'."""
        authors = []
        if not author_text:
            return authors

        # Split by "and" or "&"
        author_parts = re.split(r"\s+(?:and|&)\s+", author_text)

        for part in author_parts:
            part = part.strip()
            if not part:
                continue

            # Handle "Last, First" format
            if "," in part:
                comps = [c.strip() for c in part.split(",")]
                last_name = comps[0]
                first_name = comps[1] if len(comps) > 1 else ""
            else:
                # Assume "First Last" format
                comps = part.split()
                if len(comps) >= 2:
                    first_name = " ".join(comps[:-1])
                    last_name = comps[-1]
                else:
                    first_name = ""
                    last_name = comps[0] if comps else ""

            if last_name:
                authors.append(Author(last=last_name, first=first_name))

        return authors

    def parse_confidence(self, ref: Reference) -> float:
        """Score parse confidence for natbib format."""
        score = 0.5
        if ref.year:
            score += 0.2
        if ref.authors:
            score += 0.2
        if ref.venue:
            score += 0.1
        return min(score, 1.0)


class ACLFieldParser(NatbibFieldParser):
    """Parser for ACL-format references (natbib with year after authors)."""

    name = "acl"


class SBCFieldParser(NatbibFieldParser):
    """Parser for SBC-format references (similar to ACL natbib format)."""

    name = "sbc"


class SPLNCSFieldParser(FieldParser):
    """Parser for SPLNCS-format references (numbered format).

    Expected format:
        [N] Last, Initial.: Title. In: Venue (Year): pp. X-Y.
    """

    name = "splncs"

    YEAR_PATTERN = re.compile(r"\((\d{4})\)")
    NUMBERED_PATTERN = re.compile(r"^\s*\[(\d+)\]")

    def parse(self, raw_text: str) -> Reference:
        """Parse a SPLNCS-format reference."""
        text = raw_text.strip()
        ref = Reference(raw_text=raw_text)

        # Extract reference number
        num_match = self.NUMBERED_PATTERN.match(text)
        if num_match:
            ref.reference_number = int(num_match.group(1))
            text = text[num_match.end():].strip()

        # Extract year from (YYYY)
        year_match = self.YEAR_PATTERN.search(text)
        if year_match:
            ref.year = int(year_match.group(1))

        # Split by "In:" to get title and venue
        if "In:" in text:
            title_part, venue_part = text.split("In:", 1)
            ref.title = title_part.strip()
            # Remove authors from title (before first colon)
            if ":" in ref.title:
                ref.title = ref.title.split(":", 1)[1].strip()

            # Extract authors from the beginning
            author_text = text.split(":")[0].strip()
            if author_text:
                ref.authors = self._parse_authors(author_text)

            # Parse venue part
            venue_match = re.match(r"\s*([^(]+)\s*\(\d{4}\)", venue_part)
            if venue_match:
                ref.venue = venue_match.group(1).strip()
        else:
            # If no "In:", try to extract title and authors
            if ":" in text:
                author_part, rest = text.split(":", 1)
                ref.authors = self._parse_authors(author_part)
                ref.title = rest.strip()

        return ref

    def _parse_authors(self, author_text: str) -> list[Author]:
        """Parse SPLNCS authors (Last, Initial, Last, Initial)."""
        authors = []
        author_text = author_text.strip()

        # Remove leading [N] if present
        author_text = re.sub(r"^\s*\[\d+\]\s*", "", author_text)

        # Split by commas
        entries = self._split_author_entries(author_text)

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            # Handle "Last, Initial" or "Last, First" format
            if "," in entry:
                parts = [p.strip() for p in entry.split(",")]
                last_name = parts[0]
                first_name = parts[1] if len(parts) > 1 else ""
            else:
                # Single word (unusual, but handle it)
                last_name = entry
                first_name = ""

            if last_name:
                authors.append(Author(last=last_name, first=first_name))

        return authors

    def _split_author_entries(self, author_text: str) -> list[str]:
        """Split author entries considering commas between Last, First pairs."""
        # Pattern: "Last, First, Last, First" -> ["Last, First", "Last, First"]
        # Also handle: "Last, Initial. and Last, Initial."
        entries = []
        current = ""

        # Remove trailing punctuation
        author_text = re.sub(r"\.\s*and\s*", ", ", author_text)
        author_text = re.sub(r":\s*$", "", author_text)

        parts = author_text.split(",")
        for i, part in enumerate(parts):
            part = part.strip()

            # If this looks like a first name (single letter or short), combine with previous last name
            if i % 2 == 1:  # Odd indices are likely first names
                current = parts[i - 1].strip() + ", " + part
                entries.append(current)
            elif i == len(parts) - 1 and i % 2 == 0:  # Last part if even
                if current:
                    entries.append(current)
                else:
                    entries.append(part)

        return entries

    def parse_confidence(self, ref: Reference) -> float:
        """Score parse confidence for SPLNCS format."""
        score = 0.5
        if ref.year:
            score += 0.2
        if ref.reference_number:
            score += 0.15
        if ref.authors:
            score += 0.15
        return min(score, 1.0)
