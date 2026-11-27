"""
Persistent storage abstraction for Eu Edito & Motion Worker.
Uses EU_EDITO_STORAGE_DIR (e.g., Railway Volume /data) when configured so videos,
jobs, and rendered Motion Graphics persist across service restarts.
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
MOTION_ASSETS_DIR = STORAGE_ROOT / "_motion_assets"
MOTION_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
BROLLS_DIR = STORAGE_ROOT / "_brolls"
BROLLS_DIR.mkdir(parents=True, exist_ok=True)
CARDS_DIR = STORAGE_ROOT / "_cards"
CARDS_DIR.mkdir(parents=True, exist_ok=True)


def get_job_dir(job_id: str) -> Path:
    d = STORAGE_ROOT / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_motion_asset_path(asset_id: str, ext: str = ".mov") -> Path:
    safe = "".join(ch for ch in asset_id if ch.isalnum() or ch in ("-", "_")) or "motion"
    return MOTION_ASSETS_DIR / f"{safe}{ext}"


def cleanup_temp_dir(path: Path) -> None:
    try:
        if path.exists() and path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass


def cleanup_stale_jobs(max_age_hours: int = 48) -> int:
    """Safely prune temporary job folders older than max_age_hours (never touches _motion_assets)."""
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
