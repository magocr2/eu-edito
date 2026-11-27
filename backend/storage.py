"""
Persistent storage abstraction for Eu Edito.
Uses EU_EDITO_STORAGE_DIR (e.g., Railway Volume /data) when configured so videos and jobs persist cleanly.
"""
import os
import shutil
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def get_storage_root() -> Path:
    custom = (os.environ.get("EU_EDITO_STORAGE_DIR") or "").strip()
    if custom:
        root = Path(custom)
    elif Path("/data").exists() and os.access("/data", os.W_OK):
        root = Path("/data") / "eu_edito"
    else:
        root = BASE_DIR / "jobs_data"
    root.mkdir(parents=True, exist_ok=True)
    return root


STORAGE_ROOT = get_storage_root()
BROLLS_DIR = STORAGE_ROOT / "_brolls"
BROLLS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR = STORAGE_ROOT / "_cards"
CARDS_DIR.mkdir(parents=True, exist_ok=True)


def get_job_dir(job_id: str) -> Path:
    d = STORAGE_ROOT / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def cleanup_temp_dir(path: Path) -> None:
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def cleanup_stale_jobs(max_age_hours: int = 48) -> int:
    """Prune temporary job folders older than max_age_hours."""
    cutoff = time.time() - max(1, max_age_hours) * 3600
    removed = 0
    try:
        for item in STORAGE_ROOT.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue
            try:
                if item.stat().st_mtime < cutoff:
                    shutil.rmtree(item, ignore_errors=True)
                    removed += 1
            except Exception:
                pass
    except Exception:
        pass
    return removed
