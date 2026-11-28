"""
Eu Edito — Shared Vector Graphic Effects, Composition PNG Builder & FFmpeg Motion Compositor.
Guarantees parity between Live Web Preview and rendered MP4 exports using free/open-source Pillow + FFmpeg + libass.
"""
import math
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def _hex_to_rgb(hex_str: str, default=(255, 255, 255)):
    c = (hex_str or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return default
    try:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    except Exception:
        return default


def _hex_to_ass_bgr(hex_color: str, default="FFFFFF") -> str:
    c = (hex_color or "").strip().lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        c = default
    return f"&H00{c[4:6].upper()}{c[2:4].upper()}{c[0:2].upper()}&"


def _load_pil_font(filename: str, size: int):
    from PIL import ImageFont
    fp = FONTS_DIR / filename
    if fp.exists():
        try:
            return ImageFont.truetype(str(fp), max(10, int(size)))
        except Exception:
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None


def _wrap_text_lines(draw, text: str, font, max_w: int, max_lines: int = 3):
    words = (text or "").strip().split()
    if not words:
        return []
    lines, cur = [], []
    for w in words:
        cand = " ".join(cur + [w])
        tw = draw.textlength(cand, font=font) if hasattr(draw, "textlength") else len(cand) * 10
        if cur and tw > max_w and len(lines) < max_lines - 1:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines[:max_lines]


def ensure_rounded_mask(mask_path, w: int, h: int, radius: int = 24):
    """Create cached RGB-luminance rounded mask PNG (FFmpeg alphamerge reads Y channel)."""
    from PIL import Image, ImageDraw
    p = Path(mask_path)
    if p.exists() and p.stat().st_size > 200:
        return p
    rad = max(0, min(min(w, h) // 2, int(radius)))
    mask = Image.new("L", (w * 2, h * 2), 255 if rad <= 0 else 0)
    if rad > 0:
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=rad * 2, fill=255)
    mask = mask.resize((w, h), Image.Resampling.LANCZOS)
    mask.convert("RGB").save(str(p), "PNG")
    return p


def ensure_split_mask(mask_path, w: int, full_h: int, feather: int, side: str = "top"):
    """Create smooth luminance feather mask PNG for split-screen transitions."""
    from PIL import Image
    p = Path(mask_path)
    if p.exists() and p.stat().st_size > 200:
        return p
    feather = max(4, min(full_h // 2, int(feather)))
    col = Image.new("L", (1, full_h), 255)
    cpx = col.load()
    for y in range(feather):
        t = y / float(feather)
        s = int(255 * (t * t * (3.0 - 2.0 * t)))
        if side == "top":
            cpx[0, full_h - 1 - y] = s
        elif side == "bottom":
            cpx[0, y] = s
    alpha = col.resize((w, full_h), Image.Resampling.NEAREST)
    alpha.convert("RGB").save(str(p), "PNG")
    return p


def build_editorial_card_png(
    src_img_path,
    out_png_path,
    card_w: int = 560,
    title: str = "",
    subtitle: str = "",
    tag: str = "",
    bg_hex: str = "#FFFFFF",
    accent_hex: str = "#F472B6",
    text_hex: str = "#111827",
    radius: int = 28,
    shadow_pct: int = 55,
    angle_deg: float = 0.0,
):
    """Render an Editorial / Stacked / Storytelling Card with crisp Pillow layout + drop shadow."""
    from PIL import Image, ImageDraw, ImageFilter

    card_w = max(220, int(card_w))
    pad_x = max(18, int(card_w * 0.065))
    pad_y = max(16, int(card_w * 0.055))
    inner_w = card_w - pad_x * 2
    bg_rgb = _hex_to_rgb(bg_hex, (255, 255, 255))
    acc_rgb = _hex_to_rgb(accent_hex, (244, 114, 182))
    txt_rgb = _hex_to_rgb(text_hex, (17, 24, 39))
    is_dark_bg = (0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]) < 128
    sub_rgb = (203, 213, 225) if is_dark_bg else (71, 85, 105)
    tag_txt_rgb = (255, 255, 255) if (0.299 * acc_rgb[0] + 0.587 * acc_rgb[1] + 0.114 * acc_rgb[2]) < 165 else (15, 23, 42)

    f_tag = _load_pil_font("CreatoDisplay-Bold.otf", max(14, int(card_w * 0.044)))
    f_title = _load_pil_font("CreatoDisplay-ExtraBold.otf", max(18, int(card_w * 0.064)))
    f_sub = _load_pil_font("CreatoDisplay-Regular.otf", max(13, int(card_w * 0.042)))

    dummy = Image.new("RGBA", (card_w, 100), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dummy)

    tag_h = 0
    tag_txt = (tag or "").strip().upper()
    if tag_txt:
        tag_h = max(24, int(card_w * 0.085))

    title_lines = _wrap_text_lines(dd, title, f_title, inner_w, max_lines=2)
    sub_lines = _wrap_text_lines(dd, subtitle, f_sub, inner_w, max_lines=3)

    img_h = 0
    im_media = None
    if src_img_path and Path(src_img_path).exists():
        im_media = Image.open(str(src_img_path)).convert("RGBA")
        target_mh = int(inner_w * 0.72)
        im_media = _fit_cover_rgba(im_media, inner_w, target_mh, radius=max(10, int(radius * 0.6)))
        img_h = im_media.height

    line_h_t = int(max(22, card_w * 0.076))
    line_h_s = int(max(16, card_w * 0.052))
    gap = max(8, int(card_w * 0.028))

    cur_h = pad_y
    if tag_h:
        cur_h += tag_h + gap
    if title_lines:
        cur_h += len(title_lines) * line_h_t + gap
    if img_h:
        cur_h += img_h + (gap if sub_lines else 0)
    if sub_lines:
        cur_h += len(sub_lines) * line_h_s
    cur_h += pad_y

    body = Image.new("RGBA", (card_w, cur_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    bd.rounded_rectangle([0, 0, card_w - 1, cur_h - 1], radius=radius, fill=(*bg_rgb, 248))
    stroke_col = (255, 255, 255, 42) if is_dark_bg else (15, 23, 42, 24)
    bd.rounded_rectangle([0, 0, card_w - 1, cur_h - 1], radius=radius, outline=stroke_col, width=2)

    y = pad_y
    if tag_h:
        tw = int(bd.textlength(tag_txt, font=f_tag))
        pw = min(inner_w, tw + int(card_w * 0.09))
        bd.rounded_rectangle([pad_x, y, pad_x + pw, y + tag_h], radius=tag_h // 2, fill=(*acc_rgb, 255))
        bd.text((pad_x + (pw - tw) // 2, y + max(2, (tag_h - int(card_w * 0.046)) // 2)), tag_txt, font=f_tag, fill=(*tag_txt_rgb, 255))
        y += tag_h + gap

    for tl in title_lines:
        bd.text((pad_x, y), tl, font=f_title, fill=(*txt_rgb, 255))
        y += line_h_t
    if title_lines:
        y += gap

    if im_media is not None:
        body.paste(im_media, (pad_x, y), im_media)
        y += im_media.height + (gap if sub_lines else 0)

    for sl in sub_lines:
        bd.text((pad_x, y), sl, font=f_sub, fill=(*sub_rgb, 255))
        y += line_h_s

    if abs(angle_deg) > 0.2:
        body = body.rotate(angle_deg, resample=Image.Resampling.BICUBIC, expand=True)

    sh_alpha = int(max(0, min(100, shadow_pct)) * 1.45)
    sh_pad = 22 if sh_alpha > 10 else 4
    canvas = Image.new("RGBA", (body.width + sh_pad * 2, body.height + sh_pad * 2), (0, 0, 0, 0))
    if sh_alpha > 10:
        sh = Image.new("RGBA", body.size, (0, 0, 0, 255))
        sh.putalpha(body.getchannel("A").point(lambda v: int(v * (sh_alpha / 255.0))))
        canvas.paste(sh, (sh_pad, sh_pad + 8))
        canvas = canvas.filter(ImageFilter.GaussianBlur(7))
    canvas.paste(body, (sh_pad, sh_pad), body)
    canvas.save(str(out_png_path), "PNG")
    return Path(out_png_path), canvas.width, canvas.height


def _fit_cover_rgba(im, tw: int, th: int, radius: int = 16):
    from PIL import Image, ImageDraw
    iw, ih = im.size
    scale = max(tw / max(iw, 1), th / max(ih, 1))
    nw, nh = max(1, int(round(iw * scale))), max(1, int(round(ih * scale)))
    resized = im.resize((nw, nh), Image.Resampling.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)
    cropped = resized.crop((left, top, left + tw, top + th))
    if radius > 0:
        rm = Image.new("L", (tw, th), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, tw - 1, th - 1], radius=min(radius, tw // 2, th // 2), fill=255)
        cropped.putalpha(rm)
    return cropped


def emit_ass_graphic_fx(
    events: list,
    fx_kind: str,
    cx: int,
    cy: int,
    box_w: float,
    box_h: float,
    t0s: str,
    t1s: str,
    dur_ms: int,
    scale_f: float,
    default_accent_ass: str,
    gfx_cfg: dict | None = None,
):
    """
    Emit editable libass \\p1 vector graphic highlight synced to highlighted token timing:
    - underline: Animated Underline (ltr / rtl, configurable length, thickness, color, duration, exit)
    - circle: Circle Highlight (complete 360 or organic open ~290, size, thickness, color, duration)
    - strike: Strike Through (horizontal or diagonal, thickness, color, duration)
    - arrow: Drawn Arrow (curved / straight / angled, direction left/right/up/down, thickness, size)
    - pill: Highlight Bar expanding smoothly behind crisp bold white text
    """
    if not fx_kind or fx_kind == "none":
        return
    cfg = gfx_cfg or {}
    raw_col = (cfg.get("color") or "").strip()
    fx_color = _hex_to_ass_bgr(raw_col) if raw_col else default_accent_ass
    thick_px = float(cfg.get("thickness") or 4.5) * scale_f
    len_mult = max(0.55, min(1.40, float(cfg.get("length_pct") or cfg.get("size_pct") or 100) / 100.0))
    draw_ms = max(160, min(900, int(float(cfg.get("dur") or 0.38) * 1000)))
    anim_out = (cfg.get("anim_out") or "fade-out").lower()
    exit_dur = min(140, max(70, int(dur_ms * 0.16)))
    ex_s = max(draw_ms + 30, dur_ms - exit_dur)
    ex_t = ""
    if dur_ms > draw_ms + 80 and anim_out != "none":
        ex_t = f"\\t({ex_s},{dur_ms},2.1,\\alpha&HFF&)"

    if fx_kind == "pill":
        bw = max(84, int((box_w + 34 * scale_f) * len_mult))
        bh = max(36, int(box_h * 1.14))
        rx = max(8, min(22, int(bh * 0.25)))
        x0, y0 = int(cx - bw // 2), int(cy - bh // 2)
        path = (
            f"m {rx} 0 l {bw - rx} 0 b {bw} 0 {bw} {rx} {bw} {rx} "
            f"l {bw} {bh - rx} b {bw} {bh} {bw - rx} {bh} {bw - rx} {bh} "
            f"l {rx} {bh} b 0 {bh} 0 {bh - rx} 0 {bh - rx} "
            f"l 0 {rx} b 0 0 {rx} 0 {rx} 0"
        )
        events.append(
            f"Dialogue: 0,{t0s},{t1s},Main,,0,0,0,,"
            f"{{\\an7\\pos({x0},{y0})\\p1\\1c{fx_color}\\1a&H12&\\bord0\\shad0"
            f"\\clip({x0},{y0},{x0 + 6},{y0 + bh})\\t(0,{draw_ms},0.32,\\clip({x0},{y0},{x0 + bw},{y0 + bh})){ex_t}}}{path}{{\\p0}}"
        )
        return

    if fx_kind == "underline":
        bw = max(72, int((box_w + 22 * scale_f) * len_mult))
        lh = max(3, int(thick_px * 1.15))
        x0, y0 = int(cx - bw // 2), int(cy + box_h * 0.42)
        direction = (cfg.get("direction") or "ltr").lower()
        path = f"m 0 0 l {bw} 0 l {bw} {lh} l 0 {lh}"
        if direction == "rtl":
            c0 = f"\\clip({x0 + bw - 4},{y0 - 4},{x0 + bw},{y0 + lh + 4})"
        else:
            c0 = f"\\clip({x0},{y0 - 4},{x0 + 4},{y0 + lh + 4})"
        c1 = f"\\clip({x0},{y0 - 4},{x0 + bw},{y0 + lh + 4})"
        events.append(
            f"Dialogue: 3,{t0s},{t1s},Main,,0,0,0,,"
            f"{{\\an7\\pos({x0},{y0})\\p1\\1c{fx_color}\\1a&H00&\\bord0\\shad0\\blur1.0"
            f"{c0}\\t(40,{draw_ms},0.35,{c1}){ex_t}}}{path}{{\\p0}}"
        )
        return

    if fx_kind == "strike":
        bw = max(78, int((box_w + 26 * scale_f) * len_mult))
        lh = max(3, int(thick_px * 1.15))
        is_diag = (cfg.get("angle") or "horizontal").lower() == "diagonal"
        x0, y0 = int(cx - bw // 2), int(cy + (0 if is_diag else box_h * 0.04))
        rot = "\\frz-8" if is_diag else ""
        path = f"m 0 0 l {bw} 0 l {bw} {lh} l 0 {lh}"
        pad = 28 if is_diag else 6
        events.append(
            f"Dialogue: 3,{t0s},{t1s},Main,,0,0,0,,"
            f"{{\\an5\\pos({cx},{y0}){rot}\\p1\\1c{fx_color}\\1a&H00&\\3c&H70000000&\\bord1.2\\shad0\\blur0.8"
            f"\\clip({x0},{y0 - pad},{x0 + 4},{y0 + pad})\\t(40,{draw_ms},0.35,\\clip({x0 - 8},{y0 - pad},{x0 + bw + 8},{y0 + pad})){ex_t}}}{path}{{\\p0}}"
        )
        return

    if fx_kind == "circle":
        bw = max(92, int((box_w + 46 * scale_f) * len_mult))
        bh = max(46, int(box_h * 1.30 * len_mult))
        rx, ry = bw / 2.0, bh / 2.0
        k = 0.5523
        kx, ky = rx * k, ry * k
        x0, y0 = int(cx - rx), int(cy - ry)
        stroke = round(max(2.0, thick_px * 0.95), 1)
        complete = cfg.get("complete", True)
        if complete:
            oval_path = (
                f"m {int(rx)} 0 "
                f"b {int(rx + kx)} 0 {bw} {int(ry - ky)} {bw} {int(ry)} "
                f"b {bw} {int(ry + ky)} {int(rx + kx)} {bh} {int(rx)} {bh} "
                f"b {int(rx - kx)} {bh} 0 {int(ry + ky)} 0 {int(ry)} "
                f"b 0 {int(ry - ky)} {int(rx - kx)} 0 {int(rx)} 0"
            )
            half1 = max(120, draw_ms // 2)
            pad = int(stroke + 8)
            events.append(
                f"Dialogue: 3,{t0s},{t1s},Main,,0,0,0,,"
                f"{{\\an7\\pos({x0},{y0})\\p1\\1a&HFF&\\3c{fx_color}\\3a&H08&\\bord{stroke}\\shad0\\blur0.9"
                f"\\clip({x0 - pad},{y0 - pad},{x0},{y0 + int(ry) + 2})\\t(20,{half1},0.45,\\clip({x0 - pad},{y0 - pad},{x0 + bw + pad},{y0 + int(ry) + 2})){ex_t}}}{oval_path}{{\\p0}}"
            )
            events.append(
                f"Dialogue: 3,{t0s},{t1s},Main,,0,0,0,,"
                f"{{\\an7\\pos({x0},{y0})\\p1\\1a&HFF&\\3c{fx_color}\\3a&H08&\\bord{stroke}\\shad0\\blur0.9"
                f"\\clip({x0 + bw + pad},{y0 + int(ry) - 2},{x0 + bw + pad},{y0 + bh + pad})\\t({max(40, half1 - 40)},{draw_ms},0.45,\\clip({x0 - pad},{y0 + int(ry) - 2},{x0 + bw + pad},{y0 + bh + pad})){ex_t}}}{oval_path}{{\\p0}}"
            )
        else:
            # Organic open hand-drawn arc (~285 deg leaving gap at bottom-left)
            open_path = (
                f"m {int(rx * 0.3)} {int(bh * 0.85)} "
                f"b 0 {int(ry)} {int(rx * 0.25)} 0 {int(rx)} 0 "
                f"b {int(rx + kx)} 0 {bw} {int(ry - ky)} {bw} {int(ry)} "
                f"b {bw} {int(ry + ky)} {int(rx + kx * 0.8)} {bh} {int(rx * 0.85)} {int(bh * 0.96)}"
            )
            pad = int(stroke + 10)
            events.append(
                f"Dialogue: 3,{t0s},{t1s},Main,,0,0,0,,"
                f"{{\\an7\\pos({x0},{y0})\\p1\\1a&HFF&\\3c{fx_color}\\3a&H08&\\bord{stroke}\\shad0\\blur0.9"
                f"\\clip({x0 - pad},{y0 - pad},{x0 + 8},{y0 + bh + pad})\\t(20,{draw_ms},0.42,\\clip({x0 - pad},{y0 - pad},{x0 + bw + pad},{y0 + bh + pad})){ex_t}}}{open_path}{{\\p0}}"
            )
        return

    if fx_kind == "arrow":
        shape = (cfg.get("shape") or "curved").lower()
        direction = (cfg.get("direction") or "left").lower()
        aw = max(56, int(76 * scale_f * len_mult))
        ah = max(36, int(50 * scale_f * len_mult))
        stroke = round(max(2.2, thick_px * 0.85), 1)
        pad = int(stroke + 8)
        # Anchor near highlighted word side
        if direction == "right":
            ax = int(cx + box_w / 2 + 12 * scale_f)
            ay = int(cy - ah * 0.55)
            path = (
                f"m {aw} 0 b {int(aw*0.5)} 0 {int(aw*0.35)} {int(ah*0.65)} 4 {int(ah*0.72)} "
                f"l 18 {int(ah*0.52)} m 4 {int(ah*0.72)} l 20 {ah}"
                if shape != "straight"
                else f"m {aw} {int(ah*0.5)} l 4 {int(ah*0.5)} l 18 {int(ah*0.32)} m 4 {int(ah*0.5)} l 18 {int(ah*0.68)}"
            )
            c0 = f"\\clip({ax + aw - 4},{ay - pad},{ax + aw + pad},{ay + ah + pad})"
        elif direction == "up":
            ax = int(cx - aw // 2)
            ay = int(cy - box_h * 0.72 - ah)
            path = (
                f"m {int(aw*0.18)} 2 b {int(aw*0.75)} {int(ah*0.15)} {int(aw*0.6)} {int(ah*0.6)} {int(aw*0.5)} {ah - 4} "
                f"l {int(aw*0.34)} {ah - 18} m {int(aw*0.5)} {ah - 4} l {int(aw*0.68)} {ah - 16}"
            )
            c0 = f"\\clip({ax - pad},{ay - pad},{ax + aw + pad},{ay + 6})"
        elif direction == "down":
            ax = int(cx - aw // 2)
            ay = int(cy + box_h * 0.58)
            path = (
                f"m {int(aw*0.18)} {ah - 2} b {int(aw*0.72)} {int(ah*0.8)} {int(aw*0.55)} {int(ah*0.35)} {int(aw*0.5)} 4 "
                f"l {int(aw*0.34)} 18 m {int(aw*0.5)} 4 l {int(aw*0.68)} 18"
            )
            c0 = f"\\clip({ax - pad},{ay + ah - 6},{ax + aw + pad},{ay + ah + pad})"
        else:  # left (default: sweeps down-right from upper-left into word)
            ax = max(12, int(cx - box_w / 2 - aw - 8 * scale_f))
            ay = int(cy - ah * 0.6)
            if shape == "angled":
                path = f"m 0 2 l {int(aw*0.48)} {int(ah*0.68)} l {aw - 4} {int(ah*0.68)} l {aw - 18} {int(ah*0.48)} m {aw - 4} {int(ah*0.68)} l {aw - 18} {int(ah*0.88)}"
            elif shape == "straight":
                path = f"m 0 {int(ah*0.5)} l {aw - 4} {int(ah*0.5)} l {aw - 18} {int(ah*0.30)} m {aw - 4} {int(ah*0.5)} l {aw - 18} {int(ah*0.70)}"
            else:
                path = f"m 2 4 b {int(aw*0.18)} {int(ah*0.78)} {int(aw*0.6)} {int(ah*0.72)} {aw - 4} {int(ah*0.70)} l {aw - 18} {int(ah*0.50)} m {aw - 4} {int(ah*0.70)} l {aw - 18} {int(ah*0.90)}"
            c0 = f"\\clip({ax - pad},{ay - pad},{ax + 6},{ay + ah + pad})"

        c1 = f"\\clip({ax - pad},{ay - pad},{ax + aw + pad},{ay + ah + pad})"
        events.append(
            f"Dialogue: 3,{t0s},{t1s},Main,,0,0,0,,"
            f"{{\\an7\\pos({ax},{ay})\\p1\\1a&HFF&\\3c{fx_color}\\3a&H04&\\bord{stroke}\\shad0\\blur0.8"
            f"{c0}\\t(20,{draw_ms},0.40,{c1}){ex_t}}}{path}{{\\p0}}"
        )


def motion_overlay_expr(anim_in: str, anim_out: str, anim_dur: float, intensity: float, bs: float, be: float, tx: str, ty: str, w_even: int, h_even: int):
    """Build synchronized FFmpeg overlay (x, y) expressions for independent anim_in & anim_out."""
    dur = max(0.14, min(0.90, float(anim_dur or 0.34)))
    dist_x = int(max(36, int(w_even * 0.24 * max(0.3, min(1.6, intensity or 1.0)))))
    dist_y = int(max(36, int(h_even * 0.16 * max(0.3, min(1.6, intensity or 1.0)))))

    tin = f"min(1,max(0,(t-{bs:.3f})/{dur:.3f}))"
    ein = f"(1-(1-{tin})*(1-{tin})*(1-{tin}))"
    tout = f"min(1,max(0,({be:.3f}-t)/{dur:.3f}))"
    eout = f"(1-(1-{tout})*(1-{tout})*(1-{tout}))"

    dx_in, dy_in = "0", "0"
    if anim_in == "slide-left":
        dx_in = f"({dist_x}*(1-{ein}))"
    elif anim_in == "slide-right":
        dx_in = f"(-{dist_x}*(1-{ein}))"
    elif anim_in == "slide-up":
        dy_in = f"({dist_y}*(1-{ein}))"
    elif anim_in == "slide-down":
        dy_in = f"(-{dist_y}*(1-{ein}))"
    elif anim_in == "pop":
        dy_in = f"(-18*sin({tin}*3.1416)*(1-{tin}))"

    dx_out, dy_out = "0", "0"
    if anim_out == "slide-left":
        dx_out = f"(-{dist_x}*(1-{eout}))"
    elif anim_out == "slide-right":
        dx_out = f"({dist_x}*(1-{eout}))"
    elif anim_out == "slide-up":
        dy_out = f"(-{dist_y}*(1-{eout}))"
    elif anim_out == "slide-down":
        dy_out = f"({dist_y}*(1-{eout}))"

    ox = f"({tx})+{dx_in}+{dx_out}" if (dx_in != "0" or dx_out != "0") else tx
    oy = f"({ty})+{dy_in}+{dy_out}" if (dy_in != "0" or dy_out != "0") else ty
    return ox, oy
