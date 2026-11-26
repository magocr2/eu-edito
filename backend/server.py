"""
Hogus Studio Web — Cloud & Local PWA API Server
Serves the mobile/desktop PWA and processes videos into ready-to-post MP4 + SRT.
"""
import json
import os
import socket
import threading
import uuid
from pathlib import Path
from flask import Flask, jsonify, request, send_file, send_from_directory
from werkzeug.utils import secure_filename

from processor import (
    build_captions,
    compute_keep_ranges,
    detect_hardware,
    generate_ass,
    generate_srt,
    pick_impact_moments,
    probe_video,
    render_video,
    resolve_export_size,
    transcribe_video,
)

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
JOBS_DIR = BASE_DIR / "jobs_data"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 600 * 1024 * 1024  # 600 MB

HW_PROFILE = detect_hardware()
JOBS = {}
JOBS_LOCK = threading.Lock()


def _set_job(job_id, **updates):
    with JOBS_LOCK:
        cur = JOBS.get(job_id, {"id": job_id})
        cur.update(updates)
        JOBS[job_id] = cur
        jfile = JOBS_DIR / job_id / "job.json"
        jfile.parent.mkdir(parents=True, exist_ok=True)
        jfile.write_text(json.dumps(cur, ensure_ascii=False), encoding="utf-8")


def _get_job(job_id):
    with JOBS_LOCK:
        if job_id in JOBS:
            return dict(JOBS[job_id])
    jfile = JOBS_DIR / job_id / "job.json"
    if jfile.exists():
        return json.loads(jfile.read_text(encoding="utf-8"))
    return None


@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(str(WEB_DIR), "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def sw():
    return send_from_directory(str(WEB_DIR), "sw.js", mimetype="application/javascript")


@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(str(WEB_DIR), filename)


@app.route("/fonts/<path:filename>")
def fonts_route(filename):
    return send_from_directory(str(BASE_DIR / "fonts"), filename)


@app.route("/health")
def health():
    return jsonify({"ok": True, "hardware": HW_PROFILE["accel_label"]})


@app.route("/api/hardware")
def api_hardware():
    return jsonify(HW_PROFILE)


@app.route("/api/upload", methods=["POST"])
def api_upload():
    f = request.files.get("video")
    if not f or not f.filename:
        return jsonify({"error": "Nenhum vídeo enviado."}), 400
    job_id = uuid.uuid4().hex[:12]
    jdir = JOBS_DIR / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(f.filename) or "video.mp4"
    src_path = jdir / f"input_{safe_name}"
    f.save(str(src_path))
    _set_job(
        job_id,
        status="uploaded",
        progress=10,
        message="Vídeo recebido. Pronto para processar.",
        filename=safe_name,
        src_path=str(src_path),
    )
    return jsonify({"job_id": job_id, "filename": safe_name})


def _run_pipeline(job_id, opts):
    try:
        j = _get_job(job_id)
        src_path = Path(j["src_path"])
        jdir = JOBS_DIR / job_id

        _set_job(job_id, status="probing", progress=15, message="Analisando formato do vídeo…")
        info = probe_video(src_path)

        _set_job(job_id, status="transcribing", progress=30, message=f"Transcrevendo fala ({HW_PROFILE['accel_label']})…")
        words, dur = transcribe_video(src_path, HW_PROFILE, language=opts.get("language", "pt"))
        duration = dur or info.get("duration") or 0.0

        _set_job(job_id, status="cutting", progress=60, message="Aplicando decupagem e análise de impacto…")
        cuts_on = bool(opts.get("cuts", True))
        rhythm = opts.get("rhythm", "natural")
        keep_ranges = compute_keep_ranges(words, duration, cuts_enabled=cuts_on, rhythm=rhythm)
        captions = build_captions(words, keep_ranges, max_chars=int(opts.get("max_chars", 26)))
        impacts = pick_impact_moments(captions)

        ass_path = jdir / "captions.ass"
        srt_path = jdir / "captions.srt"
        out_mp4 = jdir / "eu_edito_pronto.mp4"

        res_choice = opts.get("resolution", "1080p")
        if HW_PROFILE.get("ram_gb", 8.0) <= 1.2 and res_choice in ("1080p", "4k"):
            res_choice = "720p"
        out_w, out_h = resolve_export_size(info["width"], info["height"], res_choice)

        generate_srt(captions, srt_path)
        generate_ass(
            captions,
            ass_path,
            width=out_w,
            height=out_h,
            style_id=opts.get("style", "dynamic-bold"),
            accent_hex=opts.get("accent_color", "#22C55E"),
            pos_y_pct=float(opts.get("pos_y", 74)),
        )

        _set_job(job_id, status="rendering", progress=78, message=f"Renderizando vídeo em alta qualidade ({out_w}x{out_h})…")
        render_video(
            src_path,
            out_mp4,
            keep_ranges,
            ass_path,
            impacts,
            HW_PROFILE,
            zoom_enabled=bool(opts.get("zoom", True)),
            width=out_w,
            height=out_h,
        )

        edited_dur = round(sum(s["e"] - s["s"] for s in keep_ranges), 1)
        removed_s = round(max(0.0, duration - edited_dur), 1)
        _set_job(
            job_id,
            status="done",
            progress=100,
            message="Vídeo pronto em alta qualidade!",
            video_url=f"/api/download/{job_id}/video",
            srt_url=f"/api/download/{job_id}/srt",
            stats={
                "captions": len(captions),
                "duration": edited_dur,
                "removed_seconds": removed_s,
                "impacts": len(impacts),
                "resolution": f"{out_w}x{out_h}",
            },
            transcript=" ".join(w["w"] for w in words),
        )
    except Exception as exc:
        _set_job(job_id, status="error", progress=0, message=str(exc))


@app.route("/api/process", methods=["POST"])
def api_process():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    j = _get_job(job_id) if job_id else None
    if not j:
        return jsonify({"error": "Job não encontrado."}), 404
    _set_job(job_id, status="queued", progress=12, message="Na fila para processamento…")
    t = threading.Thread(target=_run_pipeline, args=(job_id, data), daemon=True)
    t.start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/jobs/<job_id>")
def api_job_status(job_id):
    j = _get_job(job_id)
    if not j:
        return jsonify({"error": "Job não encontrado."}), 404
    return jsonify(j)


@app.route("/api/download/<job_id>/video")
def api_download_video(job_id):
    p = JOBS_DIR / job_id / "eu_edito_pronto.mp4"
    if not p.exists():
        return jsonify({"error": "Vídeo ainda não está pronto."}), 404
    as_att = request.args.get("dl") == "1"
    return send_file(str(p), mimetype="video/mp4", as_attachment=as_att, download_name=f"eu-edito-{job_id}.mp4")


@app.route("/api/download/<job_id>/srt")
def api_download_srt(job_id):
    p = JOBS_DIR / job_id / "captions.srt"
    if not p.exists():
        return jsonify({"error": "SRT não encontrado."}), 404
    return send_file(str(p), mimetype="application/x-subrip", as_attachment=True, download_name=f"eu-edito-{job_id}.srt")


if __name__ == "__main__":
    from waitress import create_server
    port = int(os.environ.get("PORT", "8090"))
    print(f"Hogus Studio Mobile Cloud Server listening on 0.0.0.0:{port} ({HW_PROFILE['accel_label']})")
    srv = create_server(app, host="0.0.0.0", port=port, threads=8)
    srv.run()
