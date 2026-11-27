"""
D. Animation Engine
Executes declarative `scene_plan` frames at 2x supersampling (`Image.LANCZOS`),
adding Cinema Macro-to-Reveal camera choreography, Optical Depth-of-Field blur
(`blur` plane layering), rapid-transition optical motion softening, and RGBA .mov export.
"""
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

from .assets_library import draw_scene_backdrop, ease
from .scene_composer import COMPONENT_REGISTRY


def _apply_camera(box_norm: list, z_depth: float, camera: dict, prog: float, w2: int, h2: int) -> tuple:
    bx0, by0, bx1, by1 = [float(v) for v in box_norm]
    cx0, cy0, cx1, cy1 = bx0 * w2, by0 * h2, bx1 * w2, by1 * h2

    cam_mode = (camera or {}).get("motion", "dolly_in")
    dolly_amp = float((camera or {}).get("dolly_scale", 0.05))
    pan_amp = float((camera or {}).get("pan_px", 16))
    p_s = ease(prog, "smooth")

    if cam_mode == "zoom_pan_reveal":
        # Starts zoomed-in macro gently centered, smoothly glides & pulls back to 1.0x full reveal!
        zoom_u = 1.0 - p_s
        scale = 1.0 + 0.16 * zoom_u * z_depth
        dx = (p_s - 0.5) * 14.0 * z_depth
        dy = -h2 * 0.03 * zoom_u * z_depth
    else:
        scale = 1.0 + dolly_amp * (p_s - 0.5) * z_depth if cam_mode in ("dolly_in", "orbit_3d") else 1.0
        dx = (p_s - 0.5) * pan_amp * 2.0 * z_depth if cam_mode in ("pan_sweep", "tilt_reveal") else 0.0
        dy = (p_s - 0.5) * 14.0 * z_depth if cam_mode == "tilt_reveal" else 0.0

    dy += math.sin(prog * math.pi * 2.0) * 4.0 * z_depth
    mx, my = w2 * 0.5, h2 * 0.5
    return (
        mx + (cx0 - mx) * scale + dx,
        my + (cy0 - my) * scale + dy,
        mx + (cx1 - mx) * scale + dx,
        my + (cy1 - my) * scale + dy,
    )


def render_scene_frame(scene_plan: dict, prog: float, t_sec: float, width: int = 860, height: int = 440) -> Image.Image:
    W2, H2 = max(320, int(width)) * 2, max(200, int(height)) * 2
    img = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))

    is_full = scene_plan.get("position") == "fullscreen"
    fade_in_t = 0.08 if is_full else 0.16
    fade_out_t = 0.08 if is_full else 0.12
    enter_p = ease(min(1.0, prog / fade_in_t), "cubic-out")
    exit_p = ease(min(1.0, (1.0 - prog) / fade_out_t), "smooth")
    alpha_env = max(0.0, min(1.0, min(enter_p, exit_p)))
    if alpha_env <= 0.01:
        return img.resize((width, height), Image.LANCZOS)

    palette = dict(scene_plan.get("palette") or {})
    palette.update(scene_plan.get("typography") or {})
    camera = scene_plan.get("camera") or {}
    surface_mode = scene_plan.get("surface_mode", "pure_halo")

    slide_y = int((1.0 - enter_p) * (28 if is_full else 38))
    stage_box = _apply_camera([0.02, 0.02, 0.98, 0.98], 0.35, camera, prog, W2, H2)
    stage_box = (stage_box[0], stage_box[1] + slide_y, stage_box[2], stage_box[3] + slide_y)
    draw_scene_backdrop(img, stage_box, surface_mode, palette, alpha_env, is_fullscreen=is_full)

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
        blur_r = float(layer.get("blur", 0.0))
        lbox = _apply_camera(layer.get("box", [0.05, 0.05, 0.95, 0.95]), z_d, camera, prog, W2, H2)
        lbox = (lbox[0], lbox[1] + slide_y, lbox[2], lbox[3] + slide_y)
        props = dict(layer.get("props") or {})

        if blur_r > 0.5:
            # Render onto sub-buffer and apply selective optical depth-of-field bokeh!
            sub = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
            sub_draw = ImageDraw.Draw(sub, "RGBA")
            comp_fn(sub_draw, lbox, props, local_p, t_sec, palette, alpha_env * float(layer.get("opacity", 0.55)))
            img.alpha_composite(sub.filter(ImageFilter.GaussianBlur(radius=blur_r)))
        else:
            draw = ImageDraw.Draw(img, "RGBA")
            comp_fn(draw, lbox, props, local_p, t_sec, palette, alpha_env)

    # Subtle optical entry/exit motion softening during rapid slam/exit (ref2 style)
    if prog < 0.08 or prog > 0.93:
        img = img.filter(ImageFilter.GaussianBlur(radius=2.2))

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
