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

from motion_graphics import analyze_video_for_motion, list_catalog
from motion_worker import (
    cancel_motion_task,
    enqueue_motion_render,
    ensure_motion_asset_local,
    get_task_status,
)
from processor import (
    _prepare_card_png,
    apply_manual_caption_cuts,
    build_captions,
    compute_keep_ranges,
    detect_hardware,
    generate_ass,
    generate_srt,
    pick_impact_moments,
    pick_sfx_moments,
    probe_video,
    render_video,
    resolve_export_size,
    sync_edited_captions,
    transcribe_video,
)
from storage import BROLLS_DIR, CARDS_DIR, STORAGE_ROOT, cleanup_stale_jobs, get_motion_asset_path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
JOBS_DIR = STORAGE_ROOT
JOBS_DIR.mkdir(parents=True, exist_ok=True)
cleanup_stale_jobs()

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 600 * 1024 * 1024  # 600 MB

HW_PROFILE = detect_hardware()
HW_PROFILE["max_export_res"] = "720p" if HW_PROFILE.get("ram_gb", 8.0) <= 1.2 else "4k"
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


@app.route("/api/upload_broll", methods=["POST"])
def api_upload_broll():
    f = request.files.get("broll")
    if not f or not f.filename:
        return jsonify({"error": "Nenhum B-roll enviado."}), 400
    bdir = JOBS_DIR / "_brolls"
    bdir.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(f.filename) or "broll.mp4"
    bid = f"{uuid.uuid4().hex[:10]}_{safe_name}"
    f.save(str(bdir / bid))
    return jsonify({"broll_id": bid, "filename": safe_name})


@app.route("/api/upload_card", methods=["POST"])
def api_upload_card():
    f = request.files.get("card")
    if not f or not f.filename:
        return jsonify({"error": "Nenhuma imagem enviada."}), 400
    cdir = JOBS_DIR / "_cards"
    cdir.mkdir(parents=True, exist_ok=True)
    safe_name = secure_filename(f.filename) or "card.png"
    uid = uuid.uuid4().hex[:10]
    raw_path = cdir / f"raw_{uid}_{safe_name}"
    out_name = f"{uid}_card.png"
    out_path = cdir / out_name
    f.save(str(raw_path))
    rem_bg = request.form.get("remove_bg", "1") != "0"
    _prepare_card_png(raw_path, out_path, remove_bg=rem_bg)
    try:
        raw_path.unlink(missing_ok=True)
    except Exception:
        pass
    return jsonify({"card_id": out_name, "filename": safe_name, "url": f"/api/cards/{out_name}"})


@app.route("/api/cards/<card_id>")
def api_get_card(card_id):
    p = JOBS_DIR / "_cards" / secure_filename(card_id)
    if not p.exists():
        return jsonify({"error": "Card não encontrado."}), 404
    return send_file(str(p), mimetype="image/png")


def _run_transcribe_pipeline(job_id, opts):
    try:
        j = _get_job(job_id)
        src_path = Path(j["src_path"])

        _set_job(job_id, status="probing", progress=18, message="Analisando formato do vídeo…")
        info = probe_video(src_path)

        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        accel_label = "Groq Whisper large-v3-turbo (nuvem ☁️)" if groq_key else HW_PROFILE["accel_label"]
        _set_job(job_id, status="transcribing", progress=45, message=f"Transcrevendo fala ({accel_label})…")
        words, dur = transcribe_video(src_path, HW_PROFILE, language=opts.get("language", "pt"))
        duration = dur or info.get("duration") or 0.0

        _set_job(job_id, status="cutting", progress=85, message="Preparando decupagem e legendas para revisão…")
        cuts_on = bool(opts.get("cuts", True))
        rhythm = opts.get("rhythm", "natural")
        keep_ranges = compute_keep_ranges(words, duration, cuts_enabled=cuts_on, rhythm=rhythm)
        captions = build_captions(words, keep_ranges, max_chars=int(opts.get("max_chars", 26)))

        _set_job(
            job_id,
            status="review",
            progress=100,
            message="Transcrição pronta! Confira e corrija as legendas antes de gerar o vídeo.",
            info=info,
            duration=duration,
            keep_ranges=keep_ranges,
            captions=captions,
            transcript=" ".join(w["w"] for w in words),
        )
    except Exception as exc:
        _set_job(job_id, status="error", progress=0, message=str(exc))


def _run_render_pipeline(job_id, opts):
    try:
        j = _get_job(job_id)
        src_path = Path(j["src_path"])
        jdir = JOBS_DIR / job_id
        info = j.get("info") or probe_video(src_path)
        duration = float(j.get("duration") or info.get("duration") or 0.0)
        keep_ranges = j.get("keep_ranges") or [{"s": 0.0, "e": round(duration, 3)}]

        raw_captions = opts.get("captions")
        if raw_captions is not None:
            keep_ranges, raw_captions = apply_manual_caption_cuts(keep_ranges, raw_captions)
            captions = sync_edited_captions(raw_captions)
        else:
            captions = j.get("captions") or []
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
            style_id=opts.get("style", "classic"),
            accent_hex=opts.get("accent_color", ""),
            pos_y_pct=float(opts.get("pos_y", 74)),
            caption_lines=int(opts.get("caption_lines", 3)),
            caption_scale=float(opts.get("caption_scale", 100)),
            main_font_id=opts.get("main_font", ""),
            small_font_id=opts.get("small_font", ""),
            hook_title=opts.get("hook_title", ""),
            hook_style=opts.get("hook_style", "pill-white"),
            hook_y_pct=float(opts.get("hook_y", 16)),
        )

        sfx_times = pick_sfx_moments(
            captions,
            sfx_style=opts.get("sfx_style", "auto"),
            sfx_all_highlights=bool(opts.get("sfx_all_highlights", True)),
        ) if bool(opts.get("sfx", True)) else []

        # Resolve multiple B-rolls with explicit start/end, per-caption timing, or automatic placement
        raw_brolls = list(opts.get("brolls") or [])
        if not raw_brolls and opts.get("broll_id"):
            raw_brolls = [{"id": opts["broll_id"], "layout": opts.get("broll_layout", "auto")}]
        broll_items = []
        fallback_slots = [imp[0] for imp in impacts] if impacts else [c["s"] for c in captions[::3]]
        b_slot_idx = 0
        for b in raw_brolls[:5]:
            bid = secure_filename(str(b.get("id") or "").strip())
            bp = (JOBS_DIR / "_brolls" / bid) if bid else None
            if not bp or not bp.exists():
                continue
            exp_s = b.get("start")
            exp_e = b.get("end")
            if exp_s not in (None, "") and float(exp_s) >= 0.0:
                s_t = float(exp_s)
                e_t = float(exp_e) if (exp_e not in (None, "") and float(exp_e) > s_t + 0.5) else (s_t + 3.5)
                broll_items.append({"path": bp, "layout": b.get("layout", "auto"), "start": s_t, "dur": e_t - s_t})
                continue
            marked = [c for c in captions if c.get("broll_id") == bid or (len(raw_brolls) == 1 and c.get("broll"))]
            if marked:
                for mc in marked:
                    broll_items.append({
                        "path": bp,
                        "layout": b.get("layout", "auto"),
                        "start": float(mc["s"]),
                        "dur": max(2.2, min(4.8, float(mc["e"]) - float(mc["s"]) + 0.8)),
                    })
            elif fallback_slots:
                st_t = float(fallback_slots[min(b_slot_idx, len(fallback_slots) - 1)])
                b_slot_idx += 1
                broll_items.append({"path": bp, "layout": b.get("layout", "auto"), "start": st_t, "dur": 3.5})

        # Resolve multiple floating Cards (supporting 1 or many at the same moment or spread automatically)
        raw_cards = list(opts.get("cards") or [])
        if not raw_cards and opts.get("card_id"):
            raw_cards = [{"id": opts["card_id"], "anim": opts.get("card_anim", "auto")}]
        card_items = []
        c_slot_idx = 1 if len(fallback_slots) > 1 else 0
        for crd in raw_cards[:6]:
            cid = secure_filename(str(crd.get("id") or "").strip())
            cp = (JOBS_DIR / "_cards" / cid) if cid else None
            if not cp or not cp.exists():
                continue
            marked_c = [
                c for c in captions
                if cid in (c.get("card_ids") or []) or (len(raw_cards) == 1 and c.get("card"))
            ]
            if marked_c:
                for mc in marked_c:
                    card_items.append({
                        "path": cp,
                        "anim": crd.get("anim", "auto"),
                        "start": float(mc["s"]),
                        "dur": max(2.0, min(4.5, float(mc["e"]) - float(mc["s"]) + 0.8)),
                    })
            elif fallback_slots:
                st_t = float(fallback_slots[min(c_slot_idx, len(fallback_slots) - 1)])
                c_slot_idx += 1
                card_items.append({"path": cp, "anim": crd.get("anim", "auto"), "start": st_t, "dur": 3.2})

        # Resolve approved Motion Graphics timeline layers (non-destructive transparent RGBA overlays)
        raw_motions = list(opts.get("motion_layers") or [])
        motion_items = []
        if raw_motions:
            _set_job(job_id, status="rendering", progress=68, message="Gerando camadas de Motion Graphics…")
            for ml in raw_motions[:8]:
                tid = str(ml.get("template_id") or "").strip()
                if not tid:
                    continue
                ms = max(0.0, float(ml.get("start", 0.0)))
                me = max(ms + 1.2, float(ml.get("end", ms + 3.2)))
                dur = max(1.2, min(10.0, me - ms))
                params = dict(ml.get("params") or {})
                if ml.get("position"):
                    params["position"] = ml["position"]
                mw = 440 if HW_PROFILE.get("ram_gb", 8.0) <= 1.2 else 560
                mh = 180 if HW_PROFILE.get("ram_gb", 8.0) <= 1.2 else 230
                asset_path = ensure_motion_asset_local(tid, params, duration=dur, width=mw, height=mh)
                motion_items.append({
                    "path": asset_path,
                    "start": ms,
                    "dur": dur,
                    "position": params.get("position", "top-center"),
                    "scale": float(ml.get("scale", params.get("scale", 100))),
                })

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
            studio_audio=bool(opts.get("studio_audio", False)),
            sfx_times=sfx_times,
            broll_items=broll_items,
            color_grade=bool(opts.get("color_grade", False)),
            card_items=card_items,
            motion_items=motion_items,
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
            transcript=" ".join(c["text"] for c in captions),
        )
    except Exception as exc:
        _set_job(job_id, status="error", progress=0, message=str(exc))


@app.route("/api/transcribe", methods=["POST"])
def api_transcribe():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    j = _get_job(job_id) if job_id else None
    if not j:
        return jsonify({"error": "Job não encontrado."}), 404
    _set_job(job_id, status="queued", progress=15, message="Iniciando transcrição…")
    threading.Thread(target=_run_transcribe_pipeline, args=(job_id, data), daemon=True).start()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/render", methods=["POST"])
@app.route("/api/process", methods=["POST"])
def api_render():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    j = _get_job(job_id) if job_id else None
    if not j:
        return jsonify({"error": "Job não encontrado."}), 404
    _set_job(job_id, status="rendering", progress=60, message="Preparando renderização do vídeo…")
    threading.Thread(target=_run_render_pipeline, args=(job_id, data), daemon=True).start()
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


@app.route("/api/motion/catalog")
def api_motion_catalog():
    return jsonify(list_catalog())


@app.route("/api/motion/analyze", methods=["POST"])
def api_motion_analyze():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    j = _get_job(job_id) if job_id else None
    if not j:
        return jsonify({"error": "Job não encontrado."}), 404
    caps = data.get("captions") or j.get("captions") or []
    src_path = Path(j.get("src_path", "")) if j.get("src_path") else None
    suggestions = analyze_video_for_motion(caps, video_path=src_path)
    _set_job(job_id, motion_suggestions=suggestions)
    return jsonify({"ok": True, "suggestions": suggestions})


@app.route("/api/motion/render_layer", methods=["POST"])
def api_motion_render_layer():
    data = request.get_json(silent=True) or {}
    tid = data.get("template_id", "revenue_growth")
    params = data.get("params") or {}
    dur = float(data.get("duration", 3.2))
    w = int(data.get("width", 560))
    h = int(data.get("height", 230))
    res = enqueue_motion_render(tid, params, duration=dur, width=w, height=h)
    return jsonify(res)


@app.route("/api/motion/tasks/<task_id>")
def api_motion_task_status(task_id):
    st = get_task_status(task_id)
    if not st:
        return jsonify({"error": "Task não encontrada."}), 404
    return jsonify(st)


@app.route("/api/motion/tasks/<task_id>/cancel", methods=["POST"])
def api_motion_task_cancel(task_id):
    return jsonify({"ok": cancel_motion_task(task_id)})


@app.route("/api/motion/assets/<asset_id>")
def api_motion_asset(asset_id):
    p = get_motion_asset_path(asset_id, ".mov")
    if not p.exists():
        return jsonify({"error": "Motion asset não encontrado."}), 404
    return send_file(str(p), mimetype="video/quicktime")


if __name__ == "__main__":
    if os.environ.get("SERVICE_ROLE") == "worker":
        from motion_worker import create_worker_app
        from waitress import create_server

        port = int(os.environ.get("PORT", "8091"))
        print(f"Eu Edito Motion Worker listening on 0.0.0.0:{port}")
        create_server(create_worker_app(), host="0.0.0.0", port=port, threads=6).run()
    else:
        from waitress import create_server

        port = int(os.environ.get("PORT", "8090"))
        print(f"Hogus Studio Mobile Cloud Server listening on 0.0.0.0:{port} ({HW_PROFILE['accel_label']})")
        srv = create_server(app, host="0.0.0.0", port=port, threads=8)
        srv.run()
