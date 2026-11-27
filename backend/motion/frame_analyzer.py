"""
Frame Analyzer — Visual composition analysis of original video frames via FFmpeg.
Identifies orientation, approximate speaker/face region, active gesture zone,
free negative-space zones, and frame luminance/temperature so Motion Graphics
integrate organically without obscuring faces or hands.
"""
import math
import subprocess
from pathlib import Path


def _fallback_profile(aspect: str = "portrait") -> dict:
    return {
        "analyzed": False,
        "aspect": aspect,
        "face_zone": {"x0": 0.28, "y0": 0.16, "x1": 0.72, "y1": 0.48},
        "gesture_zone": {"x0": 0.22, "y0": 0.44, "x1": 0.78, "y1": 0.68},
        "recommended_slot": "lower_stage" if aspect == "portrait" else "right_stage",
        "free_slots": ["lower_stage", "top_floating"] if aspect == "portrait" else ["right_stage", "left_stage", "lower_stage"],
        "mean_luma": 118.0,
        "color_temp": "neutral",
    }


def analyze_video_frames(video_path, timestamps=None) -> dict:
    """
    Probe dimensions and sample lightweight 64x112 raw RGB grids via FFmpeg
    to locate speaker skin/face centroids, high-motion gesture bands, and free space.
    Uses < 200KB RAM and works safely on Railway 0.5GB containers.
    """
    if not video_path or not Path(video_path).exists():
        return _fallback_profile("portrait")

    try:
        from processor import find_ffmpeg, probe_video
        ffmpeg, _ = find_ffmpeg()
        info = probe_video(video_path)
        vw = int(info.get("width") or 720)
        vh = int(info.get("height") or 1280)
        aspect = "landscape" if vw > vh * 1.1 else "portrait"
    except Exception:
        return _fallback_profile("portrait")

    gw, gh = (96, 54) if aspect == "landscape" else (54, 96)
    ts_list = [max(0.1, float(t)) for t in (timestamps or [1.0])[:3]]
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
        return _fallback_profile(aspect)

    buf = samples[0]
    skin_xs, skin_ys = [], []
    tot_luma, tot_warm = 0.0, 0.0
    zone_activity = {"top": 0.0, "mid": 0.0, "bot": 0.0, "left": 0.0, "right": 0.0}

    buf2 = samples[1] if len(samples) > 1 else None
    n_px = gw * gh

    for y in range(gh):
        ny = y / float(gh)
        for x in range(gw):
            nx = x / float(gw)
            idx = (y * gw + x) * 3
            r, g, b = buf[idx], buf[idx + 1], buf[idx + 2]
            luma = 0.299 * r + 0.587 * g + 0.114 * b
            tot_luma += luma
            tot_warm += (r - b)

            # Simple skin chromatic heuristic weighted away from extreme borders
            if 0.12 <= nx <= 0.88 and 0.08 <= ny <= 0.72:
                if r > 80 and g > 40 and b > 20 and r > g and r > b and (r - min(g, b)) > 18:
                    skin_xs.append(nx)
                    skin_ys.append(ny)

            if buf2 is not None:
                diff = abs(int(r) - int(buf2[idx])) + abs(int(g) - int(buf2[idx + 1])) + abs(int(b) - int(buf2[idx + 2]))
                if ny < 0.28:
                    zone_activity["top"] += diff
                elif ny < 0.62:
                    zone_activity["mid"] += diff
                else:
                    zone_activity["bot"] += diff
                if nx < 0.42:
                    zone_activity["left"] += diff
                elif nx > 0.58:
                    zone_activity["right"] += diff

    mean_luma = round(tot_luma / float(n_px), 1)
    warm_bias = tot_warm / float(n_px)
    color_temp = "warm" if warm_bias > 12 else ("cool" if warm_bias < -12 else "neutral")

    if len(skin_xs) >= 18:
        cx = sum(skin_xs) / len(skin_xs)
        cy = min(0.45, sum(skin_ys) / len(skin_ys))
        face_zone = {
            "x0": round(max(0.15, cx - 0.20), 2),
            "y0": round(max(0.08, cy - 0.15), 2),
            "x1": round(min(0.85, cx + 0.20), 2),
            "y1": round(min(0.62, cy + 0.16), 2),
        }
    else:
        face_zone = _fallback_profile(aspect)["face_zone"]

    # Determine quietest free space slots
    if aspect == "landscape":
        if face_zone["x0"] > 0.35 and zone_activity["left"] <= zone_activity["right"]:
            free = ["left_stage", "lower_stage", "right_stage"]
        else:
            free = ["right_stage", "lower_stage", "left_stage"]
    else:
        # Portrait talking-head: pick lower third unless face sits super low, plus top slot if quiet
        if face_zone["y1"] < 0.56:
            free = ["lower_stage", "top_floating", "asymmetric_corner"]
        else:
            free = ["top_floating", "lower_stage", "asymmetric_corner"]

    return {
        "analyzed": True,
        "aspect": aspect,
        "face_zone": face_zone,
        "gesture_zone": {"x0": 0.20, "y0": face_zone["y1"], "x1": 0.80, "y1": min(0.78, face_zone["y1"] + 0.24)},
        "recommended_slot": free[0],
        "free_slots": free,
        "mean_luma": mean_luma,
        "color_temp": color_temp,
    }
