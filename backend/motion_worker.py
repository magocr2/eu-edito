"""
Eu Edito — Motion Graphics Worker & Bounded Async Render Queue
Runs either:
1. In-process inside the main Flask server (default / single-container mode), OR
2. As an independent Railway Motion Worker service (`python backend/motion_worker.py`)
   communicating with the main service via MOTION_WORKER_URL + INTERNAL_WORKER_TOKEN.
"""
import hashlib
import json
import os
import threading
import urllib.request
import uuid
from pathlib import Path

from motion_graphics import render_motion_clip
from storage import MOTION_ASSETS_DIR, cleanup_stale_jobs, get_motion_asset_path

MAX_CONCURRENT_RENDERS = max(1, int(os.environ.get("MOTION_MAX_WORKERS", "2")))
_SEM = threading.BoundedSemaphore(MAX_CONCURRENT_RENDERS)
_JOBS = {}
_CANCEL_EVENTS = {}
_LOCK = threading.Lock()


def compute_asset_key(template_id: str, params: dict, duration: float, width: int, height: int) -> str:
    payload = json.dumps(
        {"t": template_id, "p": params or {}, "d": round(float(duration), 2), "w": int(width), "h": int(height)},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


def _set_task(task_id: str, **updates):
    with _LOCK:
        cur = _JOBS.get(task_id, {"task_id": task_id})
        cur.update(updates)
        _JOBS[task_id] = cur
        meta = MOTION_ASSETS_DIR / f"task_{task_id}.json"
        meta.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")


def get_task_status(task_id: str):
    worker_url = (os.environ.get("MOTION_WORKER_URL") or "").strip().rstrip("/")
    if worker_url and os.environ.get("SERVICE_ROLE") != "worker":
        try:
            req = urllib.request.Request(f"{worker_url}/worker/jobs/{task_id}", headers=_worker_headers())
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            pass
    with _LOCK:
        if task_id in _JOBS:
            return dict(_JOBS[task_id])
    meta = MOTION_ASSETS_DIR / f"task_{task_id}.json"
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8"))
    return None


def cancel_motion_task(task_id: str) -> bool:
    worker_url = (os.environ.get("MOTION_WORKER_URL") or "").strip().rstrip("/")
    if worker_url and os.environ.get("SERVICE_ROLE") != "worker":
        try:
            req = urllib.request.Request(
                f"{worker_url}/worker/jobs/{task_id}/cancel",
                data=b"{}",
                method="POST",
                headers={"Content-Type": "application/json", **_worker_headers()},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return bool(json.loads(r.read().decode("utf-8")).get("ok"))
        except Exception:
            return False
    with _LOCK:
        ev = _CANCEL_EVENTS.get(task_id)
        if ev:
            ev.set()
            _set_task(task_id, status="cancelled", message="Renderização cancelada.")
            return True
    return False


def _worker_headers() -> dict:
    tok = (os.environ.get("INTERNAL_WORKER_TOKEN") or "").strip()
    return {"X-Worker-Token": tok} if tok else {}


def _run_local_task(task_id: str, asset_id: str, template_id: str, params: dict, duration: float, width: int, height: int):
    cancel_ev = _CANCEL_EVENTS.get(task_id)
    out_path = get_motion_asset_path(asset_id, ".mov")
    tmp_path = MOTION_ASSETS_DIR / f"tmp_{task_id}.mov"
    try:
        if out_path.exists() and out_path.stat().st_size > 1000:
            _set_task(task_id, status="done", progress=100, asset_id=asset_id, message="Motion Graphic pronto!")
            return
        with _SEM:
            if cancel_ev and cancel_ev.is_set():
                _set_task(task_id, status="cancelled", message="Renderização cancelada.")
                return
            _set_task(task_id, status="rendering", progress=10, message="Renderizando Motion Graphic…")
            render_motion_clip(
                template_id=template_id,
                params=params,
                out_path=tmp_path,
                duration=duration,
                width=width,
                height=height,
                on_progress=lambda pct: _set_task(task_id, progress=pct),
                cancel_event=cancel_ev,
            )
            tmp_path.replace(out_path)
            _set_task(task_id, status="done", progress=100, asset_id=asset_id, message="Motion Graphic pronto!")
    except Exception as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        st = "cancelled" if (cancel_ev and cancel_ev.is_set()) else "error"
        _set_task(task_id, status=st, progress=0, message=str(exc))


def enqueue_motion_render(template_id: str, params: dict, duration: float = 3.2, width: int = 560, height: int = 230) -> dict:
    """Enqueue an async Motion Graphic render locally or via Railway Motion Worker service."""
    asset_id = compute_asset_key(template_id, params, duration, width, height)
    worker_url = (os.environ.get("MOTION_WORKER_URL") or "").strip().rstrip("/")
    if worker_url and os.environ.get("SERVICE_ROLE") != "worker":
        body = json.dumps({
            "asset_id": asset_id,
            "template_id": template_id,
            "params": params,
            "duration": duration,
            "width": width,
            "height": height,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{worker_url}/worker/render",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", **_worker_headers()},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))

    task_id = uuid.uuid4().hex[:12]
    _CANCEL_EVENTS[task_id] = threading.Event()
    _set_task(task_id, status="queued", progress=5, asset_id=asset_id, message="Na fila do Motion Worker…")
    threading.Thread(
        target=_run_local_task,
        args=(task_id, asset_id, template_id, params, duration, width, height),
        daemon=True,
    ).start()
    return {"ok": True, "task_id": task_id, "asset_id": asset_id}


def ensure_motion_asset_local(template_id: str, params: dict, duration: float = 3.2, width: int = 560, height: int = 230) -> Path:
    """Synchronous helper used during final video export to guarantee RGBA overlay exists locally."""
    asset_id = compute_asset_key(template_id, params, duration, width, height)
    local_path = get_motion_asset_path(asset_id, ".mov")
    if local_path.exists() and local_path.stat().st_size > 1000:
        return local_path

    worker_url = (os.environ.get("MOTION_WORKER_URL") or "").strip().rstrip("/")
    if worker_url and os.environ.get("SERVICE_ROLE") != "worker":
        try:
            job = enqueue_motion_render(template_id, params, duration, width, height)
            tid = job.get("task_id")
            import time
            for _ in range(90):
                st = get_task_status(tid)
                if st and st.get("status") == "done":
                    req = urllib.request.Request(f"{worker_url}/worker/assets/{asset_id}", headers=_worker_headers())
                    with urllib.request.urlopen(req, timeout=30) as r:
                        local_path.write_bytes(r.read())
                    return local_path
                if st and st.get("status") in ("error", "cancelled"):
                    break
                time.sleep(0.5)
        except Exception:
            pass

    # In-process fallback bounded by semaphore
    with _SEM:
        if local_path.exists() and local_path.stat().st_size > 1000:
            return local_path
        tmp = MOTION_ASSETS_DIR / f"sync_{uuid.uuid4().hex[:8]}.mov"
        render_motion_clip(template_id, params, tmp, duration=duration, width=width, height=height)
        tmp.replace(local_path)
    return local_path


# Standalone Railway Motion Worker Flask HTTP Service
def create_worker_app():
    from flask import Flask, jsonify, request, send_file

    wapp = Flask(__name__)

    def _auth_ok():
        expected = (os.environ.get("INTERNAL_WORKER_TOKEN") or "").strip()
        if not expected:
            return True
        return request.headers.get("X-Worker-Token", "") == expected

    @wapp.route("/health")
    def health():
        return jsonify({"ok": True, "role": "motion-worker", "max_workers": MAX_CONCURRENT_RENDERS})

    @wapp.route("/worker/render", methods=["POST"])
    def worker_render():
        if not _auth_ok():
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        tid = uuid.uuid4().hex[:12]
        asset_id = data.get("asset_id") or compute_asset_key(
            data.get("template_id", "revenue_growth"),
            data.get("params") or {},
            float(data.get("duration", 3.2)),
            int(data.get("width", 560)),
            int(data.get("height", 230)),
        )
        _CANCEL_EVENTS[tid] = threading.Event()
        _set_task(tid, status="queued", progress=5, asset_id=asset_id, message="Na fila do Motion Worker…")
        threading.Thread(
            target=_run_local_task,
            args=(
                tid,
                asset_id,
                data.get("template_id", "revenue_growth"),
                data.get("params") or {},
                float(data.get("duration", 3.2)),
                int(data.get("width", 560)),
                int(data.get("height", 230)),
            ),
            daemon=True,
        ).start()
        return jsonify({"ok": True, "task_id": tid, "asset_id": asset_id})

    @wapp.route("/worker/jobs/<task_id>")
    def worker_job_status(task_id):
        if not _auth_ok():
            return jsonify({"error": "Unauthorized"}), 401
        st = get_task_status(task_id)
        if not st:
            return jsonify({"error": "Task não encontrada"}), 404
        return jsonify(st)

    @wapp.route("/worker/jobs/<task_id>/cancel", methods=["POST"])
    def worker_job_cancel(task_id):
        if not _auth_ok():
            return jsonify({"error": "Unauthorized"}), 401
        return jsonify({"ok": cancel_motion_task(task_id)})

    @wapp.route("/worker/assets/<asset_id>")
    def worker_get_asset(asset_id):
        if not _auth_ok():
            return jsonify({"error": "Unauthorized"}), 401
        p = get_motion_asset_path(asset_id, ".mov")
        if not p.exists():
            return jsonify({"error": "Asset não encontrado"}), 404
        return send_file(str(p), mimetype="video/quicktime")

    return wapp


if __name__ == "__main__":
    from waitress import create_server

    cleanup_stale_jobs()
    port = int(os.environ.get("PORT", "8091"))
    print(f"Eu Edito Motion Worker listening on 0.0.0.0:{port} (max_workers={MAX_CONCURRENT_RENDERS})")
    create_server(create_worker_app(), host="0.0.0.0", port=port, threads=6).run()
