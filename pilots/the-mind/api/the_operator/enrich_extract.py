"""the_operator/enrich_extract.py — Helpers to convert URLs and PDFs into
plain enrichment text that can be fed into the synthesis stage.

All helpers are best-effort and bound by size limits. They raise HTTPException
on hard failures the user should see (invalid URL, unreadable PDF, oversize).
"""
from __future__ import annotations

import io
import logging
import re
from typing import Final

import httpx
from fastapi import HTTPException

logger = logging.getLogger("the_operator")

# Hard caps to keep cost / context bounded
_URL_FETCH_TIMEOUT: Final = 20  # seconds
_URL_MAX_BYTES: Final = 2_000_000  # 2 MB raw HTML
_PDF_MAX_BYTES: Final = 8_000_000  # 8 MB PDF
_OUTPUT_MAX_CHARS: Final = 5000   # matches EnrichTwinRequest.enrichment_text max


def _strip_html(html: str) -> str:
    """Crude HTML → text. Removes scripts/styles, collapses whitespace.

    Good enough for LinkedIn / company pages / blog posts. Not a full
    parser — we want signal density, not fidelity.
    """
    # Drop script/style/svg blocks entirely
    html = re.sub(r"<(script|style|svg|noscript)[^>]*>.*?</\1>", " ", html,
                  flags=re.IGNORECASE | re.DOTALL)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Decode common entities (cheap; full decode not needed for signal)
    text = (text.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&#39;", "'").replace("&quot;", '"'))
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def extract_text_from_url(url: str) -> str:
    """Fetch URL, strip HTML, return up to _OUTPUT_MAX_CHARS of text.

    Raises HTTPException(400) on invalid URL / fetch failure.
    """
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
    try:
        async with httpx.AsyncClient(
            timeout=_URL_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SimulatteOperator/1.0)"},
        ) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            raw = resp.content[:_URL_MAX_BYTES]
    except httpx.HTTPError as exc:
        logger.warning("[operator] enrich URL fetch failed for %s: %s", url, exc)
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {exc}")

    try:
        html = raw.decode(resp.encoding or "utf-8", errors="replace")
    except Exception:
        html = raw.decode("utf-8", errors="replace")

    text = _strip_html(html)
    if not text:
        raise HTTPException(status_code=400, detail="No readable text at that URL")

    return f"[URL: {url}]\n\n{text[:_OUTPUT_MAX_CHARS]}"


async def extract_text_from_pdf(pdf_bytes: bytes, filename: str = "uploaded.pdf") -> str:
    """Parse PDF bytes → text. Best-effort across PDF variants.

    Uses pypdf (pure-python). For text-heavy PDFs (LinkedIn exports, reports)
    this works well. For scanned-image PDFs it returns sparse output.

    Raises HTTPException(400) on parse failure or oversize.
    """
    if len(pdf_bytes) > _PDF_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"PDF too large ({len(pdf_bytes) // 1024}KB). Max 8MB.",
        )
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error("[operator] pypdf not installed — PDF enrichment unavailable")
        raise HTTPException(status_code=500, detail="PDF parsing not available on server")

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text: list[str] = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception as exc:  # noqa: BLE001
                logger.debug("[operator] pdf page extract failed: %s", exc)
                continue
        text = "\n".join(p for p in pages_text if p.strip())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[operator] pdf parse failed for %s: %s", filename, exc)
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {exc}")

    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        raise HTTPException(
            status_code=400,
            detail="No readable text in PDF (may be scanned/image-only — OCR not supported)",
        )

    return f"[PDF: {filename}]\n\n{text[:_OUTPUT_MAX_CHARS]}"
