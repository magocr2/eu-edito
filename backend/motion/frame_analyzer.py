"""
Frame Analyzer — Real spatial video inspection via FFmpeg lightweight sampling.
Locates face, gesture/torso activity zones, wall/background pockets, and luma
contrast across vertical and horizontal frames so Motion Graphics integrate cleanly.
"""
import subprocess
from pathlib import Path


def _default_frame_profile(aspect: str = "portrait") -> dict:
    if aspect == "landscape":
        return {
            "analyzed": False,
            "aspect": "landscape",
            "face_zone": {"x0": 0.36, "y0": 0.14, "x1": 0.64, "y1": 0.56},
            "person_zone": {"x0": 0.30, "y0": 0.14, "x1": 0.70, "y1": 0.96},
            "free_pockets": ["right_shoulder", "left_shoulder", "lower_third"],
            "best_slot": "right_shoulder",
            "bg_luma_by_zone": {"left": 115.0, "right": 115.0, "bottom": 100.0, "top": 125.0},
            "mean_luma": 115.0,
        }
    return {
        "analyzed": False,
        "aspect": "portrait",
        "face_zone": {"x0": 0.28, "y0": 0.16, "x1": 0.72, "y1": 0.50},
        "person_zone": {"x0": 0.16, "y0": 0.16, "x1": 0.86, "y1": 0.94},
        "free_pockets": ["bottom_compact", "top_left_wall", "top_band"],
        "best_slot": "bottom_compact",
        "bg_luma_by_zone": {"left": 140.0, "right": 130.0, "bottom": 90.0, "top": 150.0},
        "mean_luma": 122.0,
    }


def _zone_luma_variance(buf: bytes, gw: int, gh: int, x0f: float, y0f: float, x1f: float, y1f: float) -> tuple:
    vals = []
    ix0, ix1 = max(0, int(gw * x0f)), min(gw, int(gw * x1f))
    iy0, iy1 = max(0, int(gh * y0f)), min(gh, int(gh * y1f))
    for y in range(iy0, iy1):
        for x in range(ix0, ix1):
            idx = (y * gw + x) * 3
            vals.append(0.299 * buf[idx] + 0.587 * buf[idx + 1] + 0.114 * buf[idx + 2])
    if not vals:
        return (120.0, 20.0)
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return (round(mean, 1), round(var ** 0.5, 1))


def analyze_video_frames(video_path, timestamps=None) -> dict:
    """Inspect real video frames via FFmpeg to map subject bounds and quiet negative space."""
    if not video_path or not Path(video_path).exists():
        return _default_frame_profile("portrait")

    try:
        from processor import find_ffmpeg, probe_video
        ffmpeg, _ = find_ffmpeg()
        info = probe_video(video_path)
        vw = int(info.get("width") or 720)
        vh = int(info.get("height") or 1280)
        aspect = "landscape" if vw > vh * 1.1 else "portrait"
    except Exception:
        return _default_frame_profile("portrait")

    gw, gh = (96, 54) if aspect == "landscape" else (54, 96)
    ts_list = [max(0.08, float(t)) for t in (timestamps or [0.8, 2.0])[:3]]
    samples = []
    for t in ts_list:
        try:
            cmd = [
                ffmpeg, "-ss", f"{t:.2f}", "-i", str(video_path),
                "-frames:v", "1", "-vf", f"scale={gw}:{gh}",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=6)
            if r.returncode == 0 and len(r.stdout) >= gw * gh * 3:
                samples.append(r.stdout[: gw * gh * 3])
        except Exception:
            pass

    if not samples:
        return _default_frame_profile(aspect)

    buf = samples[0]
    skin_xs, skin_ys = [], []
    tot_luma = 0.0
    for y in range(gh):
        ny = y / float(gh)
        for x in range(gw):
            nx = x / float(gw)
            idx = (y * gw + x) * 3
            r, g, b = buf[idx], buf[idx + 1], buf[idx + 2]
            tot_luma += 0.299 * r + 0.587 * g + 0.114 * b
            if 0.12 <= nx <= 0.88 and 0.10 <= ny <= 0.64:
                if r > 80 and g > 40 and b > 20 and r > g and r > b and (r - min(g, b)) > 18:
                    skin_xs.append(nx)
                    skin_ys.append(ny)

    mean_luma = round(tot_luma / float(gw * gh), 1)
    if len(skin_xs) >= 14:
        fcx = sum(skin_xs) / len(skin_xs)
        fcy = min(0.46, sum(skin_ys) / len(skin_ys))
        face_zone = {
            "x0": round(max(0.14, fcx - 0.18), 2),
            "y0": round(max(0.08, fcy - 0.14), 2),
            "x1": round(min(0.86, fcx + 0.18), 2),
            "y1": round(min(0.56, fcy + 0.14), 2),
        }
    else:
        face_zone = _default_frame_profile(aspect)["face_zone"]

    # Score candidate pockets by distance from face & low texture clutter
    tl_luma, tl_std = _zone_luma_variance(buf, gw, gh, 0.04, 0.12, 0.44, 0.40)
    tr_luma, tr_std = _zone_luma_variance(buf, gw, gh, 0.56, 0.12, 0.96, 0.40)
    bot_luma, bot_std = _zone_luma_variance(buf, gw, gh, 0.06, 0.62, 0.94, 0.84)
    top_luma, top_std = _zone_luma_variance(buf, gw, gh, 0.10, 0.08, 0.90, 0.26)

    pockets = []
    if aspect == "landscape":
        if face_zone["x0"] >= 0.36:
            pockets.append("left_shoulder")
        if face_zone["x1"] <= 0.66:
            pockets.append("right_shoulder")
        pockets.append("bottom_compact")
    else:
        # In portrait, prefer quiet wall shoulder pockets if speaker leaves a clean side clear, else lower compact band!
        if tl_std < 38 and face_zone["x0"] > 0.32:
            pockets.append("top_left_wall")
        if tr_std < 38 and face_zone["x1"] < 0.68:
            pockets.append("top_right_wall")
        if face_zone["y0"] > 0.24 and top_std < 40:
            pockets.append("top_band")
        pockets.append("bottom_compact")

    return {
        "analyzed": True,
        "aspect": aspect,
        "face_zone": face_zone,
        "person_zone": {"x0": 0.14, "y0": face_zone["y0"], "x1": 0.86, "y1": 0.92},
        "free_pockets": pockets,
        "best_slot": pockets[0] if pockets else "bottom_compact",
        "bg_luma_by_zone": {
            "top_left": tl_luma,
            "top_right": tr_luma,
            "bottom": bot_luma,
            "top": top_luma,
        },
        "mean_luma": mean_luma,
    }
