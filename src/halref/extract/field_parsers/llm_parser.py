"""LLM-based field parser using local models via OpenAI-compatible API."""

from __future__ import annotations

import json
import logging

from halref.extract.base import FieldParser
from halref.models import Author, Reference

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a citation parser. Given ONE raw reference string from an academic bibliography (ACL, SBC, Springer/LNCS, BRACIS), extract structured fields.

The string may start with "[N] " or "N. " (reference number) followed by authors like "Last, F., Last2, G.: Title. Journal ... (YYYY). https://doi.org/..."

Return ONLY valid JSON with these fields:

{
  "title": "string",
  "authors": [{"first": "string", "last": "string"}],
  "year": integer or null,
  "venue": "string",
  "doi": "string",
  "pages": "string",
  "url": "string"
}

Rules:
- Parse author names into first and last name components (e.g. "Pitombeira-Neto, A.R." → last Pitombeira-Neto, first A.R.)
- For "et al.", include only the named authors
- Year: use the publication year in parentheses at the end of the entry (e.g. (2025)), NOT a year that appears only inside a DOI path like /ACCESS.2025./
- Venue is the journal or conference name; omit "In:" prefix if present
- doi: bare id like 10.xxxx/... ; url: full https DOI link if present
- If a field is not present, use "" or null for year
- Preserve Unicode exactly — do not strip diacritics
- Return ONLY the JSON object, no markdown fences, no extra text"""


class LLMFieldParser(FieldParser):
    """Parse references using a local LLM via OpenAI-compatible API."""

    name = "llm"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "",
        *,
        max_tokens: int = 4096,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.max_tokens = max(512, int(max_tokens))

    def is_available(self) -> bool:
        try:
            import openai  # noqa: F401
            return bool(self.model)
        except ImportError:
            return False

    def parse(self, raw_text: str) -> Reference:
        import openai

        client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "not-needed",
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.0,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content or ""
            # Try to extract JSON from the response
            data = self._extract_json(content)
            if not data:
                logger.warning(
                    "LLMFieldParser: unparseable JSON response (model=%s): %s",
                    self.model, content[:200]
                )
            return self._build_reference(raw_text, data)

        except Exception:
            # If LLM fails, return a minimally populated reference
            return Reference(raw_text=raw_text, extraction_confidence=0.0)

    def _extract_json(self, text: str) -> dict:
        """Extract JSON from LLM response, handling markdown code blocks."""
        text = text.strip()
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
        return {}

    def _build_reference(self, raw_text: str, data: dict) -> Reference:
        """Build a Reference from parsed JSON data."""
        authors = []
        for a in data.get("authors", []):
            if isinstance(a, dict):
                first = a.get("first", "")
                last = a.get("last", "")
                authors.append(Author(
                    first=first,
                    last=last,
                    full=f"{first} {last}".strip(),
                ))

        url = str(data.get("url", "") or "").strip()
        ref = Reference(
            raw_text=raw_text,
            title=data.get("title", ""),
            authors=authors,
            year=data.get("year"),
            venue=data.get("venue", ""),
            doi=data.get("doi", ""),
            pages=data.get("pages", ""),
            url=url,
        )
        ref.extraction_confidence = self.parse_confidence(ref)
        return ref

    def parse_confidence(self, ref: Reference) -> float:  # type: ignore[override]
        if not (ref.title or "").strip() or len(ref.title.strip()) < 10:
            return 0.0
        score = 0.55
        if ref.year and 1900 <= ref.year <= 2100:
            score += 0.2
        if ref.authors:
            score += 0.2
        if len(ref.title) > 28:
            score += 0.1
        return min(1.0, score)
