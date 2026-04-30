"""the_operator/storage.py — Twin JSON cache on the Railway volume.

Recon notes are cached to disk with a 14-day TTL to avoid re-running
expensive web searches. The DB is always the source of truth for the
synthesised profile. Disk cache is a read-through for recon only.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import timedelta
from pathlib import Path

from the_operator.config import RECON_CACHE_TTL_DAYS, TWIN_STALE_DAYS

logger = logging.getLogger("the_operator")

_DATA_ROOT = Path(os.environ.get("MIND_DATA_DIR", str(Path(__file__).parent.parent))).resolve()
_TWINS_DIR = _DATA_ROOT / "twins"


def _ensure_twins_dir() -> Path:
    _TWINS_DIR.mkdir(parents=True, exist_ok=True)
    return _TWINS_DIR


def recon_cache_path(twin_id: str) -> Path:
    return _ensure_twins_dir() / f"{twin_id}.recon.json"


def write_recon_cache(twin_id: str, recon_data: dict) -> None:
    """Persist raw recon intermediate to disk."""
    try:
        path = recon_cache_path(twin_id)
        path.write_text(json.dumps(recon_data, ensure_ascii=False), encoding="utf-8")
        logger.debug("[operator] recon cache written: %s", path)
    except Exception as exc:
        logger.warning("[operator] failed to write recon cache for %s: %s", twin_id, exc)


def read_recon_cache(twin_id: str, force: bool = False) -> dict | None:
    """Read recon cache if it exists and is within TTL. Returns None if stale/missing."""
    path = recon_cache_path(twin_id)
    if not path.exists():
        return None
    if force:
        return None
    age_days = (time.time() - path.stat().st_mtime) / 86400
    if age_days > RECON_CACHE_TTL_DAYS:
        logger.debug("[operator] recon cache stale (%.1f days) for %s", age_days, twin_id)
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[operator] failed to read recon cache for %s: %s", twin_id, exc)
        return None


def delete_recon_cache(twin_id: str) -> None:
    """Remove the recon cache file — called on Twin deletion."""
    path = recon_cache_path(twin_id)
    if path.exists():
        try:
            path.unlink()
        except Exception as exc:
            logger.warning("[operator] failed to delete recon cache for %s: %s", twin_id, exc)


def purge_stale_twins_from_disk(days: int = TWIN_STALE_DAYS) -> int:
    """Remove recon cache files older than `days`. Called by TTL GC loop.

    Returns count of files deleted.
    """
    cutoff = time.time() - (days * 86400)
    deleted = 0
    twins_dir = _TWINS_DIR
    if not twins_dir.exists():
        return 0
    for f in twins_dir.glob("*.recon.json"):
        try:
            if f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1
        except Exception:
            pass
    if deleted:
        logger.info("[operator] purged %d stale recon cache files", deleted)
    return deleted
