"""Optional one-shot LLM extraction: entire reference section → structured refs."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from halref.models import Author, Reference

if TYPE_CHECKING:
    from halref.config import Config

logger = logging.getLogger(__name__)

_BATCH_SYSTEM = """You are given the raw text of a single academic bibliography section (possibly Springer/LNCS/BRACIS: numbered lines like "1. Author, A.: Title. Journal ... (2020)" or "[1] Author ...").

Split it into separate references. For EACH reference return one JSON object in a JSON ARRAY (only the array, no markdown).

Each object must have:
- "title": string (paper title only; omit journal name, volume, pages, DOI URL from the title if they are clearly trailing metadata)
- "authors": array of {"first": string, "last": string} in order
- "year": integer or null (publication year in parentheses at end of the entry, not a year inside a DOI path)
- "venue": string or "" (journal or conference name if obvious)
- "doi": string or "" (only the DOI id like 10.xxxx/..., not the full URL unless no bare DOI exists)
- "pages": string or ""
- "url": string or "" (full https DOI URL if present)

Rules:
- One array element per logical bibliography entry; preserve author order.
- If the input is truncated or ambiguous, still output best-effort objects for complete entries you can identify.
- Return ONLY valid JSON (an array). No prose, no code fences."""


def references_via_llm_batch(ref_body: str, config: Config) -> list[Reference] | None:
    """Call local OpenAI-compatible API once; return References or None on failure."""
    if not (config.llm.model or "").strip():
        return None
    try:
        import openai
    except ImportError:
        logger.warning("openai not installed; pip install -e '.[llm]' for LLM batch extraction")
        return None

    text = (ref_body or "").strip()
    if len(text) < 200:
        return None
    if len(text) > 100_000:
        text = text[:100_000] + "\n\n[... truncated for model context ...]\n"

    client = openai.OpenAI(
        base_url=config.llm.base_url.rstrip("/"),
        api_key=config.llm.api_key or "not-needed",
    )
    max_out = min(int(config.llm.extract_max_tokens), 32000)

    try:
        response = client.chat.completions.create(
            model=config.llm.model,
            messages=[
                {"role": "system", "content": _BATCH_SYSTEM},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=max_out,
        )
    except Exception as exc:
        logger.warning("LLM batch request failed: %s", exc)
        return None

    content = (response.choices[0].message.content or "").strip()
    data = _parse_json_array(content)
    if not data or not isinstance(data, list):
        logger.warning("LLM batch: could not parse JSON array from response")
        return None

    refs: list[Reference] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_echo = item.get("raw")
        if isinstance(raw_echo, str) and raw_echo.strip():
            raw_text = raw_echo.strip()
        else:
            raw_text = json.dumps(item, ensure_ascii=False)[:2000]

        authors: list[Author] = []
        for a in item.get("authors") or []:
            if not isinstance(a, dict):
                continue
            first = str(a.get("first", "") or "")
            last = str(a.get("last", "") or "")
            if last or first:
                authors.append(
                    Author(first=first, last=last, full=f"{first} {last}".strip())
                )

        year = item.get("year")
        if year is not None and not isinstance(year, int):
            try:
                year = int(year)
            except (TypeError, ValueError):
                year = None

        ref = Reference(
            raw_text=raw_text,
            title=str(item.get("title", "") or "").strip(),
            authors=authors,
            year=year if isinstance(year, int) and 1900 <= year <= 2100 else None,
            venue=str(item.get("venue", "") or "").strip(),
            doi=str(item.get("doi", "") or "").strip(),
            pages=str(item.get("pages", "") or "").strip(),
            url=str(item.get("url", "") or "").strip(),
        )
        ref.extraction_confidence = 0.88 if ref.title and len(ref.title) > 12 else 0.55
        refs.append(ref)

    return refs if refs else None


def _parse_json_array(content: str) -> list | None:
    content = content.strip()
    if content.startswith("```"):
        lines = [ln for ln in content.split("\n") if not ln.strip().startswith("```")]
        content = "\n".join(lines).strip()
    try:
        data = json.loads(content)
        return data if isinstance(data, list) else None
    except json.JSONDecodeError:
        pass
    start = content.find("[")
    end = content.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            data = json.loads(content[start:end])
            return data if isinstance(data, list) else None
        except json.JSONDecodeError:
            pass
    return None
