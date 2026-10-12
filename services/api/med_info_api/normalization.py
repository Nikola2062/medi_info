from __future__ import annotations

import re
import unicodedata


HK_REGISTRATION_PATTERN = re.compile(r"(?i)(?:HK\s*[-:]?\s*)?(\d{5})")
NON_WORD_PATTERN = re.compile(r"[^\w\u3400-\u9fff]+", re.UNICODE)


def normalize_registration_number(value: str) -> str | None:
    """Return the canonical HK-XXXXX representation, or None when invalid."""
    compact = unicodedata.normalize("NFKC", value).strip()
    match = HK_REGISTRATION_PATTERN.fullmatch(compact)
    if not match:
        return None
    return f"HK-{match.group(1)}"


def extract_registration_number(value: str) -> str | None:
    """Extract the first HK registration number from OCR-like text."""
    normalized = unicodedata.normalize("NFKC", value)
    match = re.search(r"(?i)\bHK\s*[-:]?\s*(\d{5})\b", normalized)
    if not match:
        return None
    return f"HK-{match.group(1)}"


def normalize_search_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(part for part in NON_WORD_PATTERN.split(value) if part)

