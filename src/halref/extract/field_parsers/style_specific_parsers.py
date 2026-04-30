"""Style-specific field parsers for different bibliography formats."""

from __future__ import annotations

import re

from nameparser import HumanName

from halref.extract.base import FieldParser
from halref.extract.field_parsers.text_after_year import strip_leading_after_year
from halref.extract.field_parsers.year_context import pick_publication_year_match
from halref.models import Author, Reference


class NatbibFieldParser(FieldParser):
    """Base parser for natbib-style references (ACL and SBC).

    Expected format for ACL/SBC:
        Last, First and First Last. Year. Title. In Venue, pages X-Y.
    """

    name = "natbib"

    YEAR_PATTERN = re.compile(r"\b((?:19|20)\d{2})[a-z]?\b")
    VENUE_PATTERN = re.compile(
        r"\b[Ii]n:?\s+"
        r"(Proceedings\s+of\s+.*?"
        r"|Advances\s+in\s+.*?"
        r"|Anais\s+do\s+.*?"
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

        # Strip leading [N] or Springer ``N.`` reference numbers
        text = re.sub(r"^\s*\[\d+\]\s*", "", text)
        text = re.sub(r"^\s*\d{1,3}\.\s+", "", text)

        ref = Reference(raw_text=raw_text)

        # Prefer (YYYY); never treat a year inside ``/JOURNAL.2025.`` DOI slugs as publication year
        year_match = pick_publication_year_match(text)
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
            tail = text[year_match.end() :]
            stripped = strip_leading_after_year(tail)
            title_start = year_match.end() + (len(tail) - len(stripped))
            if title_start < len(text) and text[title_start : title_start + 2] == ". ":
                title_start += 2

        title_end = len(text)
        tail = text[title_start:]
        for sep in (" In: ", " In ", "\nIn: ", "\nIn "):
            rel = tail.find(sep)
            if rel != -1:
                title_end = min(title_end, title_start + rel)

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

        author_text = author_text.strip().rstrip("(").strip()
        author_text = re.sub(r",\s*et\s+al\.?$", "", author_text, flags=re.IGNORECASE).strip()
        author_text = re.sub(r"\s+et\s+al\.?$", "", author_text, flags=re.IGNORECASE).strip()
        if not author_text:
            return authors

        author_parts: list[str] = []
        for seg in re.split(r"\s+(?:and|&)\s+", author_text):
            seg = seg.strip().strip(",").strip()
            if not seg:
                continue
            paired = self._pair_surname_comma_initials(seg)
            if paired:
                author_parts.extend(paired)
            else:
                author_parts.append(seg)

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

    @staticmethod
    def _pair_surname_comma_initials(seg: str) -> list[str] | None:
        """Split ``Surname, X., Surname2, Y.`` into separate author strings.

        Returns None if the segment does not look like a comma-separated
        surname/initial list (avoids breaking corporate names).
        """
        chunks = [c.strip() for c in re.split(r",\s+", seg) if c.strip()]
        if len(chunks) < 2 or len(chunks) % 2 != 0:
            return None
        for i in range(1, len(chunks), 2):
            ini = chunks[i]
            if len(ini) > 16:
                return None
            if " " in ini and not re.match(r"^[A-Z]\.(\s+[A-Z]\.)*$", ini):
                return None
        return [f"{chunks[j]}, {chunks[j + 1]}" for j in range(0, len(chunks), 2)]

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


class SBCFieldParser(NatbibFieldParser):
    """Parser for SBC-format references (natbib format)."""

    name = "sbc"


class BRACISFieldParser(FieldParser):
    """Parser for BRACIS-format references (numbered format).

    Expected format:
        [N] Last, Initial.: Title. In: Venue (Year): pp. X-Y.
    """

    name = "bracis"

    YEAR_PATTERN = re.compile(r"\((\d{4})\)")
    NUMBERED_PATTERN = re.compile(r"^\s*\[(\d+)\]")
    NUMBERED_DOT_PATTERN = re.compile(r"^\s*(\d{1,3})\.\s+")
    DOI_PATTERN = re.compile(r"\b(10\.\d{4,}/[^\s]+)")
    # Final segment ends with ", YYYY" or " ... YYYY" (book chapters, Springer)
    _TAIL_PUBLICATION_YEAR = re.compile(r"(?:,\s*|\s+)((?:19|20)\d{2})\s*\.?\s*$")

    def parse(self, raw_text: str) -> Reference:
        """Parse a BRACIS-format reference."""
        text = raw_text.strip()
        text = re.sub(r"[\x0c\x00-\x08]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        ref = Reference(raw_text=raw_text)

        # Extract reference number: [N] or Springer/LNCS "N. Author..."
        num_match = self.NUMBERED_PATTERN.match(text)
        if num_match:
            ref.reference_number = int(num_match.group(1))
            text = text[num_match.end():].strip()
        else:
            dot_match = self.NUMBERED_DOT_PATTERN.match(text)
            if dot_match:
                ref.reference_number = int(dot_match.group(1))
                text = text[dot_match.end():].strip()

        # Split by "In:" to get title and venue
        if "In:" in text:
            # Publication year in venue: (YYYY)
            year_matches = list(self.YEAR_PATTERN.finditer(text))
            if year_matches:
                ref.year = int(year_matches[-1].group(1))
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
            journal = self._try_dot_separated_journal_article(text)
            if journal is not None:
                ref.authors = self._parse_authors(journal["authors_line"])
                ref.title = journal["title"]
                ref.venue = journal["venue"]
                ref.year = journal["year"]
            elif ":" in text:
                # Legacy: "Initials: Title" — avoid first ':' when it is volume:pages
                colon_idx = self._first_title_colon_index(text)
                if colon_idx is not None:
                    author_part, rest = text[:colon_idx], text[colon_idx + 1 :]
                    ref.authors = self._parse_authors(author_part)
                    ref.title = rest.strip()
                else:
                    author_part, rest = text.split(":", 1)
                    ref.authors = self._parse_authors(author_part)
                    ref.title = rest.strip()

        doi_m = self.DOI_PATTERN.search(raw_text) or self.DOI_PATTERN.search(text)
        if doi_m:
            ref.doi = doi_m.group(1).rstrip(".")
        url_m = re.search(r"(https?://(?:doi\.org/)?[^\s]+)", raw_text)
        if url_m:
            ref.url = url_m.group(1).rstrip(".")

        if ref.title:
            # Drop trailing DOI / URL glued after the title sentence
            ref.title = re.split(
                r"\.\s*(?:https?://|\bDOI:?\s*https?://)",
                ref.title,
                maxsplit=1,
            )[0].rstrip(". ")

        return ref

    def _parse_authors(self, author_text: str) -> list[Author]:
        """Parse BRACIS authors (Last, Initial, Last, Initial)."""
        authors = []
        author_text = author_text.strip()

        # Remove leading [N] or "N. " if present
        author_text = re.sub(r"^\s*\[\d+\]\s*", "", author_text)
        author_text = re.sub(r"^\s*\d{1,3}\.\s+", "", author_text)

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

    def _try_dot_separated_journal_article(self, text: str) -> dict[str, str | int] | None:
        """Parse ``Authors. Title. Journal, vol:pages, year.`` (no ``In:`` label).

        Springer-style numbered references often use commas and ``vol:pages`` instead
        of ``In: Venue (year)``. A naive ``split(':', 1)`` would cut inside ``553:83``.
        """
        t = text.rstrip()
        if not t.endswith("."):
            t = f"{t}."
        # Do not break on initials like "B. C." (single capital before the dot)
        parts = re.split(r"(?<![A-Z])\.\s+", t)
        parts = [p.strip() for p in parts if p.strip()]
        while len(parts) >= 2 and not self._TAIL_PUBLICATION_YEAR.search(parts[-1]):
            if len(parts) < 3:
                return None
            parts.pop()
        if len(parts) < 3:
            return None
        venue_line = parts[-1]
        ym = self._TAIL_PUBLICATION_YEAR.search(venue_line)
        if not ym:
            return None
        year = int(ym.group(1))
        tail_venue = venue_line[: ym.start()].rstrip().strip().rstrip(",")
        if not tail_venue or len(tail_venue) < 2:
            return None
        authors_line = parts[0]
        if len(authors_line) < 3:
            return None
        inner = parts[1:-1]
        if not inner:
            return None
        title = inner[0].strip()
        if not title or len(title) < 6:
            return None
        if len(inner) == 1:
            venue = tail_venue
        else:
            venue = ". ".join(inner[1:] + [tail_venue]).strip()
        return {
            "authors_line": authors_line,
            "title": title,
            "venue": venue,
            "year": year,
        }

    @staticmethod
    def _first_title_colon_index(text: str) -> int | None:
        """Index of ':' that starts the title, skipping ``volume:pages`` colons."""
        for m in re.finditer(":", text):
            i = m.start()
            window = text[max(0, i - 14) : i + 2]
            if re.search(r"\d(?:\(\d+\))?\s*:\s*\d", window):
                continue
            if re.search(r"\d+\s*:\s*\d", window):
                continue
            return i
        return None

    def parse_confidence(self, ref: Reference) -> float:
        """Score parse confidence for BRACIS format."""
        score = 0.45
        if ref.year:
            score += 0.2
        if ref.reference_number:
            score += 0.15
        if ref.authors:
            score += 0.15
        if ref.title and len(ref.title.strip()) > 18:
            score += 0.15
        return min(score, 1.0)
