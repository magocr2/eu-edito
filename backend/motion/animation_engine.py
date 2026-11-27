"""
D. Animation Engine
Executes a declarative `scene_plan` frame by frame at 2x supersampled resolution,
applying camera motion, multi-plane parallax (`z_depth`), tailored backdrop art styles,
narrative timing/easing, and exporting lossless RGBA .mov via FFmpeg.
"""
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

from .assets_library import draw_scene_backdrop, ease
from .scene_composer import COMPONENT_REGISTRY


def _apply_camera(box_norm: list, z_depth: float, camera: dict, prog: float, w2: int, h2: int) -> tuple:
    """Compute camera-transformed pixel box (dolly scale + pan sweep * parallax z_depth)."""
    bx0, by0, bx1, by1 = [float(v) for v in box_norm]
    cx0, cy0, cx1, cy1 = bx0 * w2, by0 * h2, bx1 * w2, by1 * h2

    cam_mode = (camera or {}).get("motion", "dolly_in")
    dolly_amp = float((camera or {}).get("dolly_scale", 0.04))
    pan_amp = float((camera or {}).get("pan_px", 14))
    p_s = ease(prog, "smooth")

    scale = 1.0 + dolly_amp * (p_s - 0.5) * z_depth if cam_mode in ("dolly_in", "orbit_3d") else 1.0
    dx = (p_s - 0.5) * pan_amp * 2.0 * z_depth if cam_mode in ("pan_sweep", "tilt_reveal") else 0.0
    dy = (p_s - 0.5) * 14.0 * z_depth if cam_mode == "tilt_reveal" else 0.0

    # Micro float for organic motion life
    dy += math.sin(prog * math.pi * 2.0) * 4.0 * z_depth

    mx, my = w2 * 0.5, h2 * 0.5
    nx0 = mx + (cx0 - mx) * scale + dx
    nx1 = mx + (cx1 - mx) * scale + dx
    ny0 = my + (cy0 - my) * scale + dy
    ny1 = my + (cy1 - my) * scale + dy
    return (nx0, ny0, nx1, ny1)


def render_scene_frame(scene_plan: dict, prog: float, t_sec: float, width: int = 860, height: int = 440) -> Image.Image:
    """Render one 2x supersampled RGBA frame of a declarative `scene_plan`."""
    W2, H2 = max(320, int(width)) * 2, max(200, int(height)) * 2
    img = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))

    enter_p = ease(min(1.0, prog / 0.18), "cubic-out")
    exit_p = ease(min(1.0, (1.0 - prog) / 0.14), "smooth")
    alpha_env = max(0.0, min(1.0, min(enter_p, exit_p)))
    if alpha_env <= 0.01:
        return img.resize((width, height), Image.LANCZOS)

    palette = dict(scene_plan.get("palette") or {})
    palette.update(scene_plan.get("typography") or {})
    camera = scene_plan.get("camera") or {}
    border_style = scene_plan.get("border_style", "frameless_halo")

    # Background / Art-Style Structural Stage (z=0.35 parallax)
    slide_y = int((1.0 - enter_p) * 42)
    stage_box = _apply_camera([0.03, 0.03, 0.97, 0.97], 0.35, camera, prog, W2, H2)
    stage_box = (stage_box[0], stage_box[1] + slide_y, stage_box[2], stage_box[3] + slide_y)
    draw_scene_backdrop(img, stage_box, border_style, palette, alpha_env)

    draw = ImageDraw.Draw(img, "RGBA")
    layers = sorted(scene_plan.get("layers") or [], key=lambda l: float(l.get("z_depth", 0.5)))

    for layer in layers:
        t_in = float(layer.get("t_in", 0.0))
        t_out = float(layer.get("t_out", 1.0))
        if prog < t_in or prog > t_out:
            continue
        local_p = max(0.0, min(1.0, (prog - t_in) / max(0.05, t_out - t_in)))
        comp_fn = COMPONENT_REGISTRY.get(layer.get("component"))
        if not comp_fn:
            continue
        z_d = float(layer.get("z_depth", 0.65))
        lbox = _apply_camera(layer.get("box", [0.05, 0.05, 0.95, 0.95]), z_d, camera, prog, W2, H2)
        lbox = (lbox[0], lbox[1] + slide_y, lbox[2], lbox[3] + slide_y)
        props = dict(layer.get("props") or {})
        comp_fn(draw, lbox, props, local_p, t_sec, palette, alpha_env)

    return img.resize((width, height), Image.LANCZOS)


def render_scene_clip(
    scene_plan: dict,
    out_path: Path,
    duration: float = 3.2,
    width: int = 860,
    height: int = 440,
    fps: int = 24,
    on_progress=None,
    cancel_event=None,
) -> Path:
    """Export an animated lossless RGBA `.mov` overlay clip for a `scene_plan` via FFmpeg."""
    from processor import find_ffmpeg

    ffmpeg, _ = find_ffmpeg()
    dur = max(1.2, min(10.0, float(duration or scene_plan.get("duration") or 3.2)))
    w = max(320, int(width) - (int(width) % 2))
    h = max(200, int(height) - (int(height) % 2))
    total_frames = max(12, int(round(dur * fps)))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(out_path).with_suffix(".ffmpeg.log")
    cmd = [
        ffmpeg, "-y",
        "-f", "image2pipe", "-vcodec", "png", "-r", str(fps), "-i", "-",
        "-an", "-vcodec", "png", "-pix_fmt", "rgba",
        str(out_path),
    ]
    with open(log_path, "wb") as lf:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=lf)
        try:
            for f_idx in range(total_frames):
                if cancel_event is not None and cancel_event.is_set():
                    proc.kill()
                    raise RuntimeError("Renderização cancelada.")
                prog = f_idx / float(max(1, total_frames - 1))
                t_sec = f_idx / float(fps)
                frame = render_scene_frame(scene_plan, prog, t_sec, width=w, height=h)
                frame.save(proc.stdin, format="PNG", compress_level=1)
                if on_progress and (f_idx % max(1, total_frames // 8) == 0 or f_idx == total_frames - 1):
                    on_progress(int(10 + 85 * ((f_idx + 1) / float(total_frames))))
            proc.stdin.close()
            rc = proc.wait(timeout=45)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            raise
    if rc != 0:
        err_txt = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
        try:
            log_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"Erro FFmpeg Motion Engine: {err_txt[-300:]}")
    try:
        log_path.unlink(missing_ok=True)
    except Exception:
        pass
    return Path(out_path)
