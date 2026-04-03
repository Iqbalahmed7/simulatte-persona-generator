"""
format_inferrer.py — Deterministic format detection for client data uploads.
Sprint 27 · No LLM calls.
"""

import json
import re
from enum import Enum


class DataFormat(str, Enum):
    JSON_ARRAY = "json_array"    # Top-level JSON array of strings or dicts
    JSON_LINES = "json_lines"    # One JSON object/string per line
    CSV = "csv"                  # Comma-separated values with header row
    PLAIN_TEXT = "plain_text"    # One signal per line, plain text


# ---------------------------------------------------------------------------
# BOM prefixes to strip before decoding
# ---------------------------------------------------------------------------
_BOMS = (
    b"\xef\xbb\xbf",  # UTF-8 BOM
    b"\xff\xfe",       # UTF-16 LE BOM
    b"\xfe\xff",       # UTF-16 BE BOM
)


def _strip_bom(raw: bytes) -> bytes:
    for bom in _BOMS:
        if raw.startswith(bom):
            return raw[len(bom):]
    return raw


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def infer_format(raw_bytes: bytes) -> DataFormat:
    """
    Detect the format of a client data upload from raw bytes.

    Detection order:
    1. Strip BOM (UTF-8 BOM = b'\\xef\\xbb\\xbf', UTF-16 BOM = b'\\xff\\xfe' or b'\\xfe\\xff')
    2. Decode with UTF-8 (fallback: latin-1)
    3. Strip whitespace
    4. If starts with '[': JSON_ARRAY
    5. Try to parse first non-empty line as JSON object/string:
       - If succeeds: JSON_LINES
    6. If first non-empty line contains a comma and looks like a CSV header
       (contains at least one alphabetic field): CSV
    7. Default: PLAIN_TEXT

    Never raises — falls back to PLAIN_TEXT on any error.
    """
    try:
        cleaned = _strip_bom(raw_bytes)
        text = _decode(cleaned).strip()

        if not text:
            return DataFormat.PLAIN_TEXT

        # Rule 4 — JSON array
        if text.startswith("["):
            return DataFormat.JSON_ARRAY

        # Rule 5 — JSON Lines: first non-empty line parses as a dict or string
        first_line = _first_non_empty_line(text)
        if first_line:
            try:
                parsed = json.loads(first_line)
                if isinstance(parsed, (dict, str)):
                    return DataFormat.JSON_LINES
            except (json.JSONDecodeError, ValueError):
                pass

        # Rule 6 — CSV: comma present AND at least one alphabetic character
        if "," in first_line and re.search(r"[a-zA-Z]", first_line):
            return DataFormat.CSV

    except Exception:
        pass

    return DataFormat.PLAIN_TEXT


def parse_to_signals(raw_bytes: bytes) -> list[str]:
    """
    Parse raw bytes into a flat list of signal strings.

    - JSON_ARRAY: if items are dicts, join all string values; if strings, use as-is
    - JSON_LINES: extract text/content/review/signal field or str(obj)
    - CSV: concatenate all column values per row, skip header
    - PLAIN_TEXT: one signal per non-empty line

    Returns list[str], never raises (empty list on total failure).
    """
    try:
        fmt = infer_format(raw_bytes)
        cleaned = _strip_bom(raw_bytes)
        text = _decode(cleaned).strip()

        if fmt == DataFormat.JSON_ARRAY:
            return _parse_json_array(text)

        if fmt == DataFormat.JSON_LINES:
            return _parse_json_lines(text)

        if fmt == DataFormat.CSV:
            return _parse_csv(text)

        # PLAIN_TEXT (default)
        return _parse_plain_text(text)

    except Exception:
        return []


# ---------------------------------------------------------------------------
# Format-specific parsers
# ---------------------------------------------------------------------------

def _parse_json_array(text: str) -> list[str]:
    try:
        items = json.loads(text)
        if not isinstance(items, list):
            return []
        signals: list[str] = []
        for item in items:
            if isinstance(item, str):
                signals.append(item)
            elif isinstance(item, dict):
                joined = " ".join(
                    v for v in item.values() if isinstance(v, str)
                )
                if joined:
                    signals.append(joined)
        return signals
    except Exception:
        return []


_JSON_LINES_TEXT_KEYS = ("text", "content", "review", "signal")


def _parse_json_lines(text: str) -> list[str]:
    signals: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, str):
                signals.append(obj)
            elif isinstance(obj, dict):
                # Prefer known text-field names
                extracted = None
                for key in _JSON_LINES_TEXT_KEYS:
                    if key in obj and isinstance(obj[key], str):
                        extracted = obj[key]
                        break
                if extracted is None:
                    extracted = str(obj)
                signals.append(extracted)
            else:
                signals.append(str(obj))
        except (json.JSONDecodeError, ValueError):
            pass
    return signals


def _parse_csv(text: str) -> list[str]:
    import csv
    import io

    signals: list[str] = []
    try:
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if len(rows) < 2:
            return signals
        # Skip header row (index 0)
        for row in rows[1:]:
            joined = " ".join(cell.strip() for cell in row if cell.strip())
            if joined:
                signals.append(joined)
    except Exception:
        pass
    return signals


def _parse_plain_text(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]
