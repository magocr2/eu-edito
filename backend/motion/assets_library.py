"""
Modular Visual Assets Library — Cinema-Grade Motion Design Components
Inspired by Apple Bento Hardware UI + H4Digital Editorial Storytelling:
  - Tactile squircle Bento grids with specular rims & diffused drop shadows
  - Tilted stacked highlight ribbons with optical overlap
  - Vertical scrolling roulette wheels + hand-drawn curved connector arrows
  - Optical Depth-of-Field (GaussianBlur background silhouettes behind sharp foreground hero)
  - Dramatic corner atmospheric light-leaks & 3D perspective lit meshes
"""
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FONTS_DIR = BASE_DIR / "fonts"


def load_font(filename: str, size: int):
    fp = FONTS_DIR / filename
    try:
        if fp.exists():
            return ImageFont.truetype(str(fp), max(12, int(size)))
    except Exception:
        pass
    for fb in ("CreatoDisplay-ExtraBold.otf", "CreatoDisplay-Bold.otf", "DMSans.ttf", "BebasNeue-Regular.ttf"):
        fp2 = FONTS_DIR / fb
        if fp2.exists():
            try:
                return ImageFont.truetype(str(fp2), max(12, int(size)))
            except Exception:
                pass
    return ImageFont.load_default()


def ease(t: float, mode: str = "cubic-out") -> float:
    t = max(0.0, min(1.0, float(t)))
    if mode == "spring":
        if t < 0.68:
            u = t / 0.68
            return 1.07 * (1.0 - (1.0 - u) ** 3)
        u = (t - 0.68) / 0.32
        return 1.07 - 0.07 * (u * u * (3.0 - 2.0 * u))
    if mode == "smooth":
        return t * t * (3.0 - 2.0 * t)
    return 1.0 - (1.0 - t) ** 3


def clamp_rgb(rgb, factor=1.0, offset=0):
    return tuple(max(0, min(255, int(c * factor + offset))) for c in rgb[:3])


def _v_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _v_cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _v_norm(v):
    ln = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / ln, v[1] / ln, v[2] / ln)


def _v_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _rot_pt(p, rx, ry, rz):
    x, y, z = p
    if rx:
        cx, sx = math.cos(rx), math.sin(rx)
        y, z = y * cx - z * sx, y * sx + z * cx
    if ry:
        cy, sy = math.cos(ry), math.sin(ry)
        x, z = x * cy + z * sy, -x * sy + z * cy
    if rz:
        cz, sz = math.cos(rz), math.sin(rz)
        x, y = x * cz - y * sz, x * sz + y * cz
    return (x, y, z)


# ---------------------------------------------------------------------------
# TRUE 3D PERSPECTIVE MESH ENGINE
# ---------------------------------------------------------------------------

def render_3d_faces(draw: ImageDraw.ImageDraw, faces: list, cx: int, cy: int, scale: float, rx: float, ry: float, rz: float, alpha_env: float, light_dir=(0.45, -0.70, 0.55), fov: float = 4.2):
    ld = _v_norm(light_dir)
    view_dir = (0.0, 0.0, 1.0)
    projected = []
    for verts, base_rgb, metallic in faces:
        rverts = [_rot_pt(v, rx, ry, rz) for v in verts]
        if len(rverts) < 3:
            continue
        n = _v_norm(_v_cross(_v_sub(rverts[1], rverts[0]), _v_sub(rverts[2], rverts[0])))
        ndotl = max(0.20, abs(_v_dot(n, ld)))
        spec = 0.0
        if metallic:
            hv = _v_norm((ld[0] + view_dir[0], ld[1] + view_dir[1], ld[2] + view_dir[2]))
            spec = pow(max(0.0, abs(_v_dot(n, hv))), 14.0) * 115.0
        avg_z = sum(v[2] for v in rverts) / float(len(rverts))
        pts2d = [(cx + x * scale * (fov / max(1.2, fov - z)), cy + y * scale * (fov / max(1.2, fov - z))) for x, y, z in rverts]
        lit_rgb = clamp_rgb(base_rgb, 0.44 + 0.68 * ndotl, spec)
        edge_rgb = clamp_rgb(base_rgb, 1.18, 28)
        projected.append((avg_z, pts2d, lit_rgb, edge_rgb))

    projected.sort(key=lambda item: item[0])
    a = int(248 * alpha_env)
    ea = int(175 * alpha_env)
    for _, pts2d, fill_c, edge_c in projected:
        draw.polygon(pts2d, fill=(*fill_c, a), outline=(*edge_c, ea))


def build_box_mesh(w: float, h: float, d: float, offset=(0.0, 0.0, 0.0), color=(96, 165, 250), metallic=True):
    ox, oy, oz = offset
    hx, hy, hz = w * 0.5, h * 0.5, d * 0.5
    v = [
        (ox - hx, oy - hy, oz + hz), (ox + hx, oy - hy, oz + hz),
        (ox + hx, oy + hy, oz + hz), (ox - hx, oy + hy, oz + hz),
        (ox - hx, oy - hy, oz - hz), (ox + hx, oy - hy, oz - hz),
        (ox + hx, oy + hy, oz - hz), (ox - hx, oy + hy, oz - hz),
    ]
    quads = [
        [v[0], v[1], v[2], v[3]], [v[5], v[4], v[7], v[6]],
        [v[4], v[0], v[3], v[7]], [v[1], v[5], v[6], v[2]],
        [v[4], v[5], v[1], v[0]], [v[3], v[2], v[6], v[7]],
    ]
    return [(q, color, metallic) for q in quads]


def build_cylinder_mesh(radius: float, height: float, segs: int = 12, offset=(0.0, 0.0, 0.0), color=(250, 204, 21), metallic=True):
    ox, oy, oz = offset
    hy = height * 0.5
    top_ring = [(ox + radius * math.cos(2 * math.pi * i / segs), oy - hy, oz + radius * math.sin(2 * math.pi * i / segs)) for i in range(segs)]
    bot_ring = [(ox + radius * math.cos(2 * math.pi * i / segs), oy + hy, oz + radius * math.sin(2 * math.pi * i / segs)) for i in range(segs)]
    faces = [(top_ring, clamp_rgb(color, 1.12, 16), metallic), (list(reversed(bot_ring)), clamp_rgb(color, 0.72), metallic)]
    for i in range(segs):
        j = (i + 1) % segs
        faces.append(([top_ring[i], top_ring[j], bot_ring[j], bot_ring[i]], color, metallic))
    return faces


def build_octahedron_mesh(radius: float, offset=(0.0, 0.0, 0.0), color=(34, 211, 238), metallic=True):
    ox, oy, oz = offset
    top = (ox, oy - radius * 1.2, oz)
    bot = (ox, oy + radius * 1.2, oz)
    ring = [(ox + radius, oy, oz), (ox, oy, oz + radius), (ox - radius, oy, oz), (ox, oy, oz - radius)]
    faces = []
    for i in range(4):
        j = (i + 1) % 4
        faces.append(([top, ring[i], ring[j]], color, metallic))
        faces.append(([bot, ring[j], ring[i]], clamp_rgb(color, 0.8), metallic))
    return faces


# ---------------------------------------------------------------------------
# ATMOSPHERIC SCRIMS, LIGHT LEAKS, TACTILE TILES & HAND-DRAWN ARROWS
# ---------------------------------------------------------------------------

def draw_scene_backdrop(img: Image.Image, box: tuple, surface_mode: str, palette: dict, alpha_env: float, is_fullscreen: bool = False):
    """
    Full-canvas atmospheric studio lighting (for fullscreen cutaways) OR
    feathered ambient radial scrims (for integrated presenter overlays).
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    sec = palette["secondary"]
    bg = palette["bg"]

    if is_fullscreen:
        # Cinema full-bleed backdrop + diagonal blurred atmospheric color light-leaks (ref2_18 / ref1_02 look!)
        draw = ImageDraw.Draw(img, "RGBA")
        if surface_mode == "paper_cutaway":
            base_c = (242, 240, 235)
            leak_c = prim
            leak_a = int(42 * alpha_env)
        elif surface_mode == "bento_studio":
            base_c = (210, 214, 219)
            leak_c = (155, 162, 170)
            leak_a = int(85 * alpha_env)
        else:
            base_c = bg
            leak_c = prim
            leak_a = int(125 * alpha_env)
        draw.rectangle([0, 0, img.width, img.height], fill=(*base_c, min(255, int(255 * min(1.0, alpha_env * 1.15)))))

        leak = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(leak)
        W, H = img.size
        ld.ellipse([int(W * 0.52), -int(H * 0.12), int(W * 1.15), int(H * 0.36)], fill=(*leak_c, leak_a))
        ld.ellipse([-int(W * 0.18), int(H * 0.68), int(W * 0.45), int(H * 1.12)], fill=(*leak_c, int(leak_a * 0.85)))
        img.alpha_composite(leak.filter(ImageFilter.GaussianBlur(radius=95)))
        return

    # Feathered floating overlay scrim strictly inset from borders (even wide vignette, zero spotlight blobs)
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pad_x = max(90, (x1 - x0) // 10)
    pad_y = max(72, (y1 - y0) // 8)
    gd.ellipse([x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y], fill=(*bg, int(170 * alpha_env)))
    gd.ellipse([x0 + pad_x + 20, y0 + pad_y + 12, x1 - pad_x - 20, y1 - pad_y - 12], fill=(*prim, int(24 * alpha_env)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=52)))

    draw = ImageDraw.Draw(img, "RGBA")
    if surface_mode == "scrim_brackets":
        L = 24
        ca = int(210 * alpha_env)
        for cx, cy, dx, dy in ((x0 + 36, y0 + 28, 1, 1), (x1 - 36, y0 + 28, -1, 1), (x0 + 36, y1 - 28, 1, -1), (x1 - 36, y1 - 28, -1, -1)):
            draw.line([(cx, cy), (cx + dx * L, cy)], fill=(*prim, ca), width=3)
            draw.line([(cx, cy), (cx, cy + dy * L)], fill=(*prim, ca), width=3)
    elif surface_mode == "swiss_pillar":
        draw.line([(x0 + 48, y0 + 36), (x0 + 48, y1 - 36)], fill=(*prim, int(235 * alpha_env)), width=6)
    elif surface_mode in ("hairline_floating", "chronicle_rule"):
        draw.line([(x0 + 54, y0 + 26), (x1 - 54, y0 + 26)], fill=(*prim, int(170 * alpha_env)), width=2)


def _draw_shadow_text(draw: ImageDraw.ImageDraw, pos: tuple, txt: str, font, fill: tuple, anchor: str = "lm", shadow_a: int = 195):
    x, y = int(pos[0]), int(pos[1])
    draw.text((x + 3, y + 4), txt, font=font, fill=(0, 0, 0, shadow_a), anchor=anchor)
    draw.text((x, y), txt, font=font, fill=fill, anchor=anchor)


def _draw_compact_tag(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str, font, palette: dict, alpha_env: float, accent_border: bool = True):
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    px, py = max(20, tw // 2 + 22), max(16, th // 2 + 12)
    prim = palette["primary"]
    bg = palette["bg"]
    draw.rounded_rectangle([cx - px, cy - py, cx + px, cy + py], radius=py, fill=(*bg, int(222 * alpha_env)), outline=(*prim, int((200 if accent_border else 85) * alpha_env)), width=2)
    draw.text((cx, cy), text, font=font, fill=(*palette["text"], int(252 * alpha_env)), anchor="mm")


def _draw_squircle_tile(draw: ImageDraw.ImageDraw, box, radius: int, fill_rgb: tuple, rim_rgb: tuple, alpha_env: float):
    """Tactile Apple-style rounded tile with diffused soft drop-shadow and inner specular rim."""
    x0, y0, x1, y1 = [int(v) for v in box]
    draw.rounded_rectangle([x0 + 6, y0 + 12, x1 + 6, y1 + 14], radius=radius, fill=(0, 0, 0, int(65 * alpha_env)))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(*fill_rgb, int(248 * alpha_env)), outline=(*rim_rgb, int(90 * alpha_env)), width=2)


def _draw_hand_loop_arrow(draw: ImageDraw.ImageDraw, p_start: tuple, p_end: tuple, col: tuple, prog: float, alpha_env: float):
    """Draw curved editorial loop arrow (ref2_14 style) connecting callout bubble to hero headline."""
    sx, sy = p_start
    ex, ey = p_end
    pts = []
    steps = 34
    n_draw = max(2, int(steps * min(1.0, prog)))
    for i in range(n_draw):
        u = i / float(steps - 1)
        # Smooth loop swirl midway
        loop_x = 46 * math.sin(u * math.pi * 2.1) * (1.0 - u)
        loop_y = -24 * math.sin(u * math.pi * 2.0) * math.sin(u * math.pi)
        px = sx + (ex - sx) * u + loop_x
        py = sy + (ey - sy) * u + loop_y
        pts.append((px, py))
    if len(pts) >= 2:
        draw.line(pts, fill=(*col, int(248 * alpha_env)), width=5, joint="curve")
        if prog > 0.78:
            hx, hy = pts[-1]
            px0, py0 = pts[-2]
            ang = math.atan2(hy - py0, hx - px0)
            a1, a2 = ang + 2.55, ang - 2.55
            draw.polygon([(hx, hy), (hx + 22 * math.cos(a1), hy + 22 * math.sin(a1)), (hx + 22 * math.cos(a2), hy + 22 * math.sin(a2))], fill=(*col, int(248 * alpha_env)))


# ---------------------------------------------------------------------------
# REFERENCE-GRADE PRO COMPONENTS (Bento Grid, Stacked Ribbons, Roulette, Spotlight)
# ---------------------------------------------------------------------------

def comp_bento_macro(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """
    Apple Hardware Bento Grid (Ref 1): contrasting matte dark & light squircle tiles
    with animated analog clock, segmented progress blocks, glowing calendar dots, & status bar.
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    gw, gh = x1 - x0, y1 - y0
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.72), "cubic-out")
    dark_t = (15, 16, 20)
    light_t = (246, 247, 250)
    pad = 20

    # Top Bento Row: Left Light Analog Clock Tile | Right Dark Info / Metric Tile
    top_h = int(gh * 0.34)
    split_x = x0 + int(gw * 0.44)
    _draw_squircle_tile(draw, [x0, y0, split_x - pad // 2, y0 + top_h], 44, light_t, (255, 255, 255), alpha_env)
    _draw_squircle_tile(draw, [split_x + pad // 2, y0, x1, y0 + top_h], 44, dark_t, (90, 95, 105), alpha_env)

    # Analog Clock Face inside Top-Left Tile
    ck_cx, ck_cy = (x0 + split_x - pad // 2) // 2, y0 + top_h // 2
    ck_r = min(split_x - x0, top_h) // 2 - 22
    draw.ellipse([ck_cx - ck_r, ck_cy - ck_r, ck_cx + ck_r, ck_cy + ck_r], fill=(235, 237, 242, int(245 * alpha_env)))
    for tk in range(12):
        ta = math.radians(tk * 30 - 90)
        draw.line([(ck_cx + ck_r * 0.80 * math.cos(ta), ck_cy + ck_r * 0.80 * math.sin(ta)), (ck_cx + ck_r * 0.92 * math.cos(ta), ck_cy + ck_r * 0.92 * math.sin(ta))], fill=(90, 95, 105, int(220 * alpha_env)), width=3)
    # Sweeping red second hand + dark minute hand
    sec_a = -math.pi / 2 + t_sec * 2.8 + anim * math.pi * 1.6
    min_a = -math.pi * 0.65 + anim * 0.5
    draw.line([(ck_cx, ck_cy), (ck_cx + ck_r * 0.64 * math.cos(min_a), ck_cy + ck_r * 0.64 * math.sin(min_a))], fill=(20, 22, 26, int(250 * alpha_env)), width=6)
    draw.line([(ck_cx, ck_cy), (ck_cx + ck_r * 0.82 * math.cos(sec_a), ck_cy + ck_r * 0.82 * math.sin(sec_a))], fill=(239, 68, 68, int(248 * alpha_env)), width=4)
    draw.ellipse([ck_cx - 6, ck_cy - 6, ck_cx + 6, ck_cy + 6], fill=(239, 68, 68, int(252 * alpha_env)))

    # Top-Right Dark Tile: Route / Key Stat Info
    tr_x0 = split_x + pad // 2
    f_tr_t = load_font("CreatoDisplay-Bold.otf", 34)
    f_tr_b = load_font("DMSans.ttf", 28)
    lbls = p.get("labels") or ["Escala Real", "Entregas no Prazo", "Meta 100%"]
    top_hdr = str(p.get("threshold_label") or lbls[0])[:20]
    draw.text((tr_x0 + 32, y0 + 50), top_hdr, font=f_tr_t, fill=(255, 255, 255, int(248 * alpha_env)), anchor="lm")
    draw.line([(tr_x0 + 32, y0 + 82), (x1 - 32, y0 + 82)], fill=(255, 255, 255, int(35 * alpha_env)), width=2)
    b_rows = [it for it in lbls if str(it).strip()][:3] or ["Sistema Ativo", "Fluxo Contínuo"]
    for li, it in enumerate(b_rows[:2]):
        yy = y0 + 132 + li * 74
        draw.ellipse([tr_x0 + 34, yy - 9, tr_x0 + 52, yy + 9], fill=(*prim, int(245 * alpha_env)))
        draw.text((tr_x0 + 70, yy), str(it)[:22], font=f_tr_b, fill=(224, 230, 238, int(245 * alpha_env)), anchor="lm")

    # Middle Wide Hero Bento Card: Title + Sparkline + 3D/Gradient Progress Ribbon
    mid_y0 = y0 + top_h + pad
    mid_h = int(gh * 0.28)
    _draw_squircle_tile(draw, [x0, mid_y0, x1, mid_y0 + mid_h], 44, (14, 24, 18), prim, alpha_env)
    f_mid_h = load_font("CreatoDisplay-ExtraBold.otf", 48)
    f_mid_s = load_font("DMSans.ttf", 28)
    f_mid_m = load_font("BebasNeue-Regular.ttf", 76)
    nums = p.get("numbers") or []
    hero_num = nums[0] if nums else "100%"
    draw.text((x0 + 36, mid_y0 + 56), str(p.get("title") or lbls[0])[:22], font=f_mid_h, fill=(255, 255, 255, int(252 * alpha_env)), anchor="lm")
    draw.text((x0 + 36, mid_y0 + 108), str(p.get("accent") or "em evolução contínua")[:28], font=f_mid_s, fill=(180, 224, 195, int(230 * alpha_env)), anchor="lm")
    draw.text((x1 - 40, mid_y0 + 66), hero_num[:10], font=f_mid_m, fill=(*prim, int(252 * alpha_env)), anchor="rm")
    # Crisp sparkline curve across middle-right empty cavity
    sp_pts = []
    for si in range(max(2, int(24 * anim))):
        u = si / 23.0
        sp_pts.append((x0 + 36 + int((x1 - x0 - 72) * u), mid_y0 + mid_h - 84 - int(46 * (u ** 1.35) + 8 * math.sin(u * 8))))
    if len(sp_pts) >= 2:
        draw.line(sp_pts, fill=(*prim, int(195 * alpha_env)), width=5, joint="curve")
    # Glowing full progress bar along bottom of wide card
    pb_x0, pb_y0, pb_x1, pb_y1 = x0 + 36, mid_y0 + mid_h - 52, x1 - 36, mid_y0 + mid_h - 26
    draw.rounded_rectangle([pb_x0, pb_y0, pb_x1, pb_y1], radius=13, fill=(255, 255, 255, int(42 * alpha_env)))
    draw.rounded_rectangle([pb_x0, pb_y0, pb_x0 + max(26, int((pb_x1 - pb_x0) * anim)), pb_y1], radius=13, fill=(*prim, int(250 * alpha_env)))

    # Bottom Bento Row: Left Segmented Battery/Metric Tile | Right Dark Dot Matrix Grid
    bot_y0 = mid_y0 + mid_h + pad
    bot_h = y1 - bot_y0
    bot_split = x0 + int(gw * 0.42)
    _draw_squircle_tile(draw, [x0, bot_y0, bot_split - pad // 2, y1], 44, light_t, (255, 255, 255), alpha_env)
    _draw_squircle_tile(draw, [bot_split + pad // 2, bot_y0, x1, y1], 44, dark_t, (90, 95, 105), alpha_env)

    # Segmented Energy Blocks in Bottom-Left Light Tile
    f_pct = load_font("CreatoDisplay-ExtraBold.otf", 54)
    pct_val = int(round(88 * anim))
    draw.text(((x0 + bot_split - pad // 2) // 2, bot_y0 + 66), f"{pct_val}%", font=f_pct, fill=(25, 28, 34, int(245 * alpha_env)), anchor="mm")
    seg_x0 = x0 + 32
    seg_w = max(28, (bot_split - pad // 2 - x0 - 64 - 4 * 10) // 5)
    for si in range(5):
        lit = (si / 5.0) < anim
        sx = seg_x0 + si * (seg_w + 10)
        scol = (249, 115, 22, int(248 * alpha_env)) if lit else (222, 226, 232, int(240 * alpha_env))
        draw.rounded_rectangle([sx, bot_y0 + 122, sx + seg_w, y1 - 36], radius=10, fill=scol)

    # Interactive Dot Matrix Calendar/Milestone Grid in Bottom-Right Dark Tile
    br_x0 = bot_split + pad // 2
    draw.text((br_x0 + 30, bot_y0 + 46), "Progresso Ativo", font=f_tr_t, fill=(255, 255, 255, int(245 * alpha_env)), anchor="lm")
    cols, rows = 6, 3
    cell_x = (x1 - br_x0 - 64) // cols
    cell_y = max(44, (bot_h - 104) // rows)
    lit_limit = int(anim * (cols * rows * 0.72))
    idx_dot = 0
    for r in range(rows):
        for c in range(cols):
            dx = br_x0 + 48 + c * cell_x
            dy = bot_y0 + 108 + r * cell_y
            is_hi = idx_dot < lit_limit
            is_alert = idx_dot == lit_limit - 1 and lit_limit > 2
            dcol = (220, 38, 38) if is_alert else ((163, 230, 53) if is_hi else (42, 46, 54))
            draw.ellipse([dx - 18, dy - 18, dx + 18, dy + 18], fill=(*dcol, int(248 * alpha_env)))
            idx_dot += 1


def comp_stacked_ribbons(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """
    H4Digital Slanted Stacked Ribbons (Ref 2 ref2_10): rotated high-contrast typography strips
    alternating vivid accent fill & matte obsidian, slamming sequentially with spring bounce!
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    raw_items = [str(it).strip() for it in (p.get("labels") or []) if str(it).strip()]
    for cand in (p.get("title"), p.get("accent"), "Na Prática"):
        if cand and len(raw_items) < 3 and str(cand).strip() not in raw_items:
            raw_items.append(str(cand).strip())
    items = [it[:22] for it in raw_items[:3]]

    # Draw directly onto temporary layer rotated slightly per ribbon then composite onto image
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    f_rib = load_font("CreatoDisplay-ExtraBold.otf", 60)
    angles = (-3.6, 2.2, -1.8)
    for idx, txt in enumerate(items):
        enter_t = max(0.0, (prog - idx * 0.14) / 0.22)
        if enter_t <= 0.0:
            continue
        sp = ease(min(1.0, enter_t), "spring")
        ry = cy - 105 + idx * 108 + int((1.0 - sp) * 65)
        is_dark = (idx % 2 == 1)
        bg_c = (15, 16, 20) if is_dark else prim
        fg_c = prim if is_dark else (12, 14, 18)

        bb = draw.textbbox((0, 0), txt, font=f_rib)
        rw = min(x1 - x0 - 40, max(440, (bb[2] - bb[0]) + 128))
        rh = 92
        # Approximated rotated parallelogram ribbon (fast & zero-artifact in 2x!)
        ang = math.radians(angles[idx % len(angles)])
        dx_a = math.sin(ang) * (rh * 0.5)
        dy_a = math.sin(ang) * (rw * 0.5)
        poly = [
            (cx - rw * 0.5 + dx_a, ry - rh * 0.5 - dy_a),
            (cx + rw * 0.5 + dx_a, ry - rh * 0.5 + dy_a),
            (cx + rw * 0.5 - dx_a, ry + rh * 0.5 + dy_a),
            (cx - rw * 0.5 - dx_a, ry + rh * 0.5 - dy_a),
        ]
        # Soft drop shadow
        sh_poly = [(px + 6, py + 12) for px, py in poly]
        draw.polygon(sh_poly, fill=(0, 0, 0, int(95 * alpha_env)))
        draw.polygon(poly, fill=(*bg_c, int(250 * alpha_env)))
        draw.text((cx, ry), txt, font=f_rib, fill=(*fg_c, int(252 * alpha_env)), anchor="mm")


def comp_year_roulette(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """
    H4Digital Scrolling Chrono Roulette + Popping Speech Pill + Hand-Drawn Arrow -> Takeaway (Ref 2 ref2_14).
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.68), "cubic-out")
    nums = p.get("numbers") or p.get("labels") or ["2024", "2025", "2026"]
    if len(nums) < 3:
        try:
            base_y = int(re.sub(r"[^\d]", "", str(nums[0])) or 2026) if nums else 2026
            slot_vals = [str(base_y - 1), str(base_y), str(base_y + 1)]
        except Exception:
            slot_vals = ["Fase 1", str(nums[0] if nums else "Atual"), "Próximo"]
    else:
        slot_vals = [str(x)[:10] for x in nums[:3]]

    cx = (x0 + x1) // 2 - 90
    cy_mid = (y0 + y1) // 2 - 60
    f_big = load_font("CreatoDisplay-ExtraBold.otf", 92)
    f_dim = load_font("CreatoDisplay-ExtraBold.otf", 72)

    # Vertical roulette rolling upward into active focal row
    roll_off = int((1.0 - anim) * 140)
    for row_i, val in enumerate(slot_vals):
        ry = cy_mid + (row_i - 1) * 104 + roll_off
        active = (row_i == 1)
        col = prim if active else palette["muted"]
        al = int((252 if active else 75) * alpha_env)
        draw.text((cx, ry), val, font=f_big if active else f_dim, fill=(*col, al), anchor="mm")

    # Popped Speech Pill beside active row + hand-drawn loop arrow down to hero headline!
    if prog > 0.22:
        raw_pill = str(p.get("threshold_label") or slot_vals[1]).replace("META: ", "").strip()[:14]
        pill_txt = f"MARCO {raw_pill}" if raw_pill.isdigit() else raw_pill
        f_pill = load_font("CreatoDisplay-ExtraBold.otf", 38)
        bb = draw.textbbox((0, 0), pill_txt, font=f_pill)
        pw = max(145, (bb[2] - bb[0]) + 52)
        num_bb = draw.textbbox((cx, cy_mid), slot_vals[1], font=f_big, anchor="mm")
        px = num_bb[2] + 34 + pw // 2
        py = cy_mid
        draw.rounded_rectangle([px - pw // 2, py - 38, px + pw // 2, py + 38], radius=22, fill=(*prim, int(248 * alpha_env)))
        draw.polygon([(px - pw // 2 + 2, py), (px - pw // 2 - 18, py + 2), (px - pw // 2 + 2, py + 16)], fill=(*prim, int(248 * alpha_env)))
        draw.text((px, py), pill_txt, font=f_pill, fill=(255, 255, 255, int(252 * alpha_env)), anchor="mm")

        # Hand-drawn loop arrow completes swiftly down into takeaway text below!
        arr_p = max(0.0, min(1.0, (prog - 0.24) / 0.36))
        hero_y = y1 - 110
        _draw_hand_loop_arrow(draw, (px, py + 44), (cx + 120, hero_y - 68), prim, arr_p, alpha_env)

    # Sharp editorial takeaway bottom center
    f_tk1 = load_font("DMSans.ttf", 38)
    f_tk2 = load_font("CreatoDisplay-ExtraBold.otf", 80)
    hero_y = y1 - 110
    _draw_shadow_text(draw, ((x0 + x1) // 2, hero_y - 44), str(p.get("title") or "")[:24], f_tk1, (*palette["text"], int(250 * alpha_env)), anchor="mm")
    _draw_shadow_text(draw, ((x0 + x1) // 2, hero_y + 20), str(p.get("accent") or "EM EVOLUÇÃO")[:22], f_tk2, (*prim, int(252 * alpha_env)), anchor="mm")


def comp_spotlight_emblem(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Ref 2 Circular Ring Spotlight + Satellite Callout Badge + Rising Hero Bars inside ring."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    anim = ease(min(1.0, prog / 0.72), "spring")
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 20
    rad = min(x1 - x0, y1 - y0) // 2 - 36

    # Delicate circular aperture ring
    draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(*palette["text"], int(150 * alpha_env)), width=2)
    # Floating accent badge on circumference (10:30 position rotating subtly)
    ang = math.radians(-135 + math.sin(t_sec * 1.4) * 8)
    bx = cx + int(rad * math.cos(ang))
    by = cy + int(rad * math.sin(ang))
    draw.ellipse([bx - 42, by - 42, bx + 42, by + 42], fill=(*prim, int(250 * alpha_env)))
    # Simple megaphone/spark inside satellite badge
    draw.polygon([(bx - 16, by + 4), (bx + 14, by - 16), (bx + 14, by + 18)], fill=(255, 255, 255, int(250 * alpha_env)))

    # Crisp rising staircase bars + upward arrow inside ring
    bar_w, gap = 36, 18
    bx0 = cx - (4 * bar_w + 3 * gap) // 2
    by_base = cy + int(rad * 0.42)
    for bi in range(4):
        bh = int((50 + bi * 34) * anim)
        x_b = bx0 + bi * (bar_w + gap)
        draw.rectangle([x_b, by_base - bh, x_b + bar_w, by_base], fill=(*prim, int(248 * alpha_env)))
    # Upward trend polyline with arrowhead
    ap0 = (bx0, by_base - int(72 * anim))
    ap1 = (bx0 + 100, by_base - int(112 * anim))
    ap2 = (bx0 + 180, by_base - int(182 * anim))
    draw.line([ap0, ap1, ap2], fill=(*prim, int(252 * alpha_env)), width=10, joint="curve")


# ---------------------------------------------------------------------------
# ENHANCED DOMAIN COMPONENTS (3D, Geo, Sci, Mech, Editorial)
# ---------------------------------------------------------------------------

def comp_3d_coins_growth(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.72), "spring")
    gw, gh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 10

    hy = y0 + int(gh * 0.36)
    draw.line([(x0 + 18, hy), (x1 - 18, hy)], fill=(*prim, int(170 * alpha_env)), width=2)
    thresh_lbl = p.get("threshold_label") or ""
    if thresh_lbl:
        f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 24)
        _draw_compact_tag(draw, x0 + 115, hy - 22, thresh_lbl[:18], f_sm, palette, alpha_env)

    for col in (-1, 0, 1):
        scx = cx + col * int(gw * 0.22)
        draw.ellipse([scx - 52, y1 - 32, scx + 52, y1 - 8], fill=(0, 0, 0, int(115 * alpha_env)))

    faces = []
    for col, count in ((0, 2), (1, 4), (2, 7)):
        shown_n = max(1, int(count * anim))
        for k in range(shown_n):
            faces.extend(build_cylinder_mesh(
                0.34, 0.14, segs=12,
                offset=(-1.1 + col * 1.1, 0.85 - k * 0.24, 0.0),
                color=sec if col == 2 else clamp_rgb(sec, 0.85),
                metallic=True,
            ))
    render_3d_faces(draw, faces, cx, cy, scale=min(gw * 0.24, gh * 0.58), rx=0.28, ry=t_sec * 0.65, rz=0.0, alpha_env=alpha_env)


def comp_3d_pillars_scale(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    anim = ease(min(1.0, prog / 0.72), "cubic-out")
    vals = p.get("values") or [25, 48, 76, 100]
    vmax = max(vals) or 100.0
    gw, gh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 12

    faces = []
    n = min(4, len(vals))
    for i in range(n):
        h_3d = max(0.25, 1.8 * (vals[i] / vmax) * anim)
        col = prim if i == n - 1 else clamp_rgb(prim, 0.45, 25)
        faces.extend(build_box_mesh(0.46, h_3d, 0.46, offset=(-1.35 + i * 0.90, 0.95 - h_3d * 0.5, 0.0), color=col, metallic=True))
    render_3d_faces(draw, faces, cx, cy, scale=min(gw * 0.24, gh * 0.58), rx=0.24, ry=-0.42 + math.sin(t_sec * 0.8) * 0.12, rz=0.0, alpha_env=alpha_env)

    nums = p.get("numbers") or []
    if nums:
        f_num = load_font(palette.get("headline_font", "BebasNeue-Regular.ttf"), 42)
        _draw_compact_tag(draw, x1 - 95, y0 + 36, nums[0][:10], f_num, palette, alpha_env)


def comp_tactical_radar(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    rad = min(x1 - x0, y1 - y0) // 2 - 12
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "cubic-out")

    draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(8, 14, 22, int(210 * alpha_env)), outline=(*prim, int(190 * alpha_env)), width=3)
    draw.line([(cx - rad, cy), (cx + rad, cy)], fill=(*prim, int(55 * alpha_env)), width=1)
    draw.line([(cx, cy - rad), (cx, cy + rad)], fill=(*prim, int(55 * alpha_env)), width=1)
    for rf in (0.36, 0.68):
        rr = int(rad * rf)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*prim, int(115 * alpha_env)), width=2)

    ang_deg = int((t_sec * 120) % 360)
    draw.pieslice([cx - rad + 4, cy - rad + 4, cx + rad - 4, cy + rad - 4], start=ang_deg - 40, end=ang_deg, fill=(*prim, int(68 * alpha_env)))

    lbls = p.get("labels") or []
    tags = lbls if len(lbls) >= 2 else ["Setor N", "Cerco L", "Base S", "Alvo"]
    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
    for ui, ang in enumerate((-140, -35, 45, 140)):
        dist = rad * (0.98 - 0.54 * anim)
        ux = cx + int(dist * math.cos(math.radians(ang)))
        uy = cy + int(dist * math.sin(math.radians(ang)))
        draw.line([(ux, uy), (cx, cy)], fill=(*sec, int(155 * alpha_env)), width=2)
        draw.ellipse([ux - 8, uy - 8, ux + 8, uy + 8], fill=(*sec, int(250 * alpha_env)), outline=(255, 255, 255, int(220 * alpha_env)), width=2)
        if ui < len(tags):
            _draw_shadow_text(draw, (ux, uy - 18), str(tags[ui])[:12], f_sm, (*palette["text"], int(245 * alpha_env)), anchor="mb")

    pulse = 14 + int(8 * abs(math.sin(t_sec * 5.0)))
    draw.ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], outline=(*sec, int(240 * alpha_env)), width=3)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(*sec, int(250 * alpha_env)))


def comp_geo_route_map(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    gw, gh = x1 - x0, y1 - y0

    for k in range(3):
        yy = y0 + int(gh * (0.28 + 0.24 * k))
        draw.arc([x0 - 80, yy - 30, x1 + 80, yy + 90], start=195, end=345, fill=(*sec, int(68 * alpha_env)), width=2)

    places = p.get("labels") or ["Origem", "Escala", "Destino"]
    n_pins = max(2, min(4, len(places)))
    pts = [
        (x0 + int(gw * (0.14 + 0.72 * i / float(max(1, n_pins - 1)))), y0 + int(gh * (0.68 if i % 2 == 0 else 0.30)))
        for i in range(n_pins)
    ]

    for i in range(n_pins - 1):
        p0, p1 = pts[i], pts[i + 1]
        apts = []
        steps = 28
        for si in range(max(2, int(steps * anim))):
            u = si / float(steps - 1)
            apts.append((int(p0[0] + (p1[0] - p0[0]) * u), int(p0[1] + (p1[1] - p0[1]) * u - 62 * math.sin(math.pi * u))))
        if len(apts) >= 2:
            draw.line(apts, fill=(*prim, int(245 * alpha_env)), width=7, joint="curve")
            hx, hy = apts[-1]
            draw.ellipse([hx - 9, hy - 9, hx + 9, hy + 9], fill=(255, 255, 255, int(252 * alpha_env)))

    f_lbl = load_font(palette.get("body_font", "DMSans.ttf"), 24)
    for i, (px, py) in enumerate(pts):
        pulse = 16 + int(8 * abs(math.sin(t_sec * 4.2 + i)))
        draw.ellipse([px - pulse, py - pulse, px + pulse, py + pulse], outline=(*prim, int(155 * alpha_env)), width=2)
        draw.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(*prim, int(252 * alpha_env)), outline=(255, 255, 255, int(250 * alpha_env)), width=3)
        _draw_compact_tag(draw, px, py + 36, str(places[i])[:14], f_lbl, palette, alpha_env)


def comp_machine_cutaway(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    gw, gh = x1 - x0, y1 - y0
    cy = (y0 + y1) // 2

    def _draw_pro_gear(gcx, gcy, r, teeth, rot_rad, col):
        pts = []
        for k in range(teeth * 2):
            a = rot_rad + (k * math.pi) / teeth
            rr = r if k % 2 == 0 else r * 0.78
            pts.append((gcx + rr * math.cos(a), gcy + rr * math.sin(a)))
        draw.polygon(pts, fill=(*clamp_rgb(col, 0.35), int(225 * alpha_env)), outline=(*col, int(250 * alpha_env)))
        draw.ellipse([gcx - r * 0.58, gcy - r * 0.58, gcx + r * 0.58, gcy + r * 0.58], outline=(*col, int(130 * alpha_env)), width=2)
        draw.ellipse([gcx - r * 0.28, gcy - r * 0.28, gcx + r * 0.28, gcy + r * 0.28], fill=(*palette["bg"], int(245 * alpha_env)), outline=(*col, int(250 * alpha_env)), width=3)
        for sp in range(3):
            sa = rot_rad + sp * (2 * math.pi / 3.0)
            draw.line([(gcx + r * 0.28 * math.cos(sa), gcy + r * 0.28 * math.sin(sa)), (gcx + r * 0.58 * math.cos(sa), gcy + r * 0.58 * math.sin(sa))], fill=(*col, int(210 * alpha_env)), width=4)

    g1x, g1y, r1 = x0 + int(gw * 0.22), cy, min(gh * 0.40, gw * 0.16)
    g2x, g2y, r2 = g1x + int(r1 * 1.66), cy - int(r1 * 0.22), r1 * 0.72
    rot1 = t_sec * 1.45
    rot2 = -rot1 * (10.0 / 7.0) + 0.22
    _draw_pro_gear(g1x, g1y, r1, 10, rot1, prim)
    _draw_pro_gear(g2x, g2y, r2, 7, rot2, sec)

    px_base = g2x + int(r2 * 0.85) + 28
    chamber_x1 = min(x1 - 16, px_base + int(gw * 0.38))
    stroke = int(26 * math.sin(t_sec * 4.0))
    draw.rounded_rectangle([px_base, cy - 42, chamber_x1, cy + 42], radius=14, fill=(8, 22, 42, int(205 * alpha_env)), outline=(*prim, int(225 * alpha_env)), width=3)
    crank_x = g2x + int(r2 * 0.44 * math.cos(rot2))
    crank_y = g2y + int(r2 * 0.44 * math.sin(rot2))
    phead_x = px_base + 54 + stroke
    draw.line([(crank_x, crank_y), (phead_x, cy)], fill=(*sec, int(245 * alpha_env)), width=7)
    draw.rounded_rectangle([phead_x - 16, cy - 32, phead_x + 16, cy + 32], radius=6, fill=(*sec, int(235 * alpha_env)), outline=(255, 255, 255, int(220 * alpha_env)), width=2)
    if chamber_x1 - (phead_x + 22) > 20:
        draw.rounded_rectangle([phead_x + 20, cy - 30, chamber_x1 - 8, cy + 30], radius=8, fill=(*prim, int(85 * alpha_env)))

    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
    for lx, ltxt in ((g1x, "Torque"), (g2x, "Transmissão"), ((px_base + chamber_x1) // 2, "Pressão")):
        _draw_shadow_text(draw, (lx, y1 - 14), ltxt, f_sm, (*palette["text"], int(245 * alpha_env)), anchor="mb")


def comp_science_orbital(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    gw, gh = x1 - x0, y1 - y0
    acx, acy = x0 + int(gw * 0.28), (y0 + y1) // 2
    rad = int(min(gw * 0.24, gh * 0.42))

    draw.ellipse([acx - 24, acy - 24, acx + 24, acy + 24], fill=(*sec, int(248 * alpha_env)), outline=(255, 255, 255, int(225 * alpha_env)), width=3)
    for oi, tilt in enumerate((0.2, 1.25, 2.3)):
        op_pts = []
        for s in range(44):
            a = 2 * math.pi * s / 43.0
            rx = acx + rad * math.cos(a) * math.cos(tilt) - rad * 0.42 * math.sin(a) * math.sin(tilt)
            ry = acy + rad * math.cos(a) * math.sin(tilt) + rad * 0.42 * math.sin(a) * math.cos(tilt)
            op_pts.append((rx, ry))
        draw.line(op_pts, fill=(*prim, int(175 * alpha_env)), width=3)
        pa = t_sec * (2.3 + oi * 0.6) + oi * 2.1
        px = acx + rad * math.cos(pa) * math.cos(tilt) - rad * 0.42 * math.sin(pa) * math.sin(tilt)
        py = acy + rad * math.cos(pa) * math.sin(tilt) + rad * 0.42 * math.sin(pa) * math.cos(tilt)
        draw.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(255, 255, 255, int(252 * alpha_env)), outline=(*sec, int(250 * alpha_env)), width=3)

    wx0, wx1 = x0 + int(gw * 0.56), x1 - 24
    wy_mid = (y0 + y1) // 2
    wave_pts = [(wx0 + int((wx1 - wx0) * (i / 39.0)), wy_mid + int(56 * math.sin((i / 39.0) * math.pi * 4.5 - t_sec * 5.2) * math.sin((i / 39.0) * math.pi))) for i in range(40)]
    draw.line(wave_pts, fill=(*sec, int(248 * alpha_env)), width=6, joint="curve")
    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 22)
    _draw_compact_tag(draw, (wx0 + wx1) // 2, y1 - 24, "ÓRBITA • ONDA • ENERGIA", f_sm, palette, alpha_env, accent_border=False)


def comp_ai_neural_architecture(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    for ni, ny in enumerate((y0 + 36, cy, y1 - 36)):
        lx0, rx1 = x0 + 32, x1 - 32
        draw.line([(lx0, ny), (cx - 80, cy)], fill=(*prim, int(145 * alpha_env)), width=3)
        draw.line([(cx + 80, cy), (rx1, ny)], fill=(*sec, int(145 * alpha_env)), width=3)
        u = (t_sec * 1.15 + ni * 0.33) % 1.0
        px = int(lx0 + (cx - 80 - lx0) * u)
        py = int(ny + (cy - ny) * u)
        draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(255, 255, 255, int(250 * alpha_env)))
        draw.ellipse([lx0 - 10, ny - 10, lx0 + 10, ny + 10], fill=(*prim, int(240 * alpha_env)))
        draw.ellipse([rx1 - 10, ny - 10, rx1 + 10, ny + 10], fill=(*sec, int(240 * alpha_env)))

    faces = build_octahedron_mesh(0.75, color=prim, metallic=True)
    render_3d_faces(draw, faces, cx, cy, scale=112, rx=0.32, ry=t_sec * 1.25, rz=0.15, alpha_env=alpha_env)


def comp_chronology_archive(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.80), "cubic-out")
    cy = (y0 + y1) // 2 + 8

    draw.line([(x0 + 44, cy), (x1 - 44, cy)], fill=(*sec, int(85 * alpha_env)), width=4)
    draw.line([(x0 + 44, cy), (x0 + 44 + int((x1 - x0 - 88) * anim), cy)], fill=(*prim, int(248 * alpha_env)), width=6)

    items = p.get("labels") or ["Início", "Virada", "Legado"]
    n = max(2, min(4, len(items)))
    f_yr = load_font(palette.get("headline_font", "AppleGaramond-BoldItalic.ttf"), 38)
    f_tx = load_font(palette.get("body_font", "DMSans.ttf"), 24)

    for i in range(n):
        ix = x0 + 96 + int(((x1 - x0 - 192) * i) / float(max(1, n - 1)))
        lit = anim >= i / float(n)
        lbl = str(items[i])[:14]
        col = prim if lit else palette["muted"]
        draw.ellipse([ix - 12, cy - 12, ix + 12, cy + 12], fill=(*col, int(250 * alpha_env)), outline=(255, 255, 255, int(230 * alpha_env)), width=3)
        dy_off = -54 if i % 2 == 0 else 54
        draw.line([(ix, cy), (ix, cy + dy_off)], fill=(*col, int(190 * alpha_env)), width=2)
        _draw_compact_tag(draw, ix, cy + dy_off + (-16 if i % 2 == 0 else 16), lbl, f_yr if len(lbl) <= 6 else f_tx, palette, alpha_env, accent_border=lit)


def comp_editorial_comparison(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.72), "cubic-out")
    lbls = p.get("labels") or ["Opção A", "Opção B"]
    vals = p.get("values") or [35, 92]
    vmax = max(vals[:2] or [100]) or 100.0
    gw = x1 - x0
    f_lbl = load_font(palette.get("body_font", "DMSans.ttf"), 24)
    f_val = load_font(palette.get("headline_font", "CreatoDisplay-ExtraBold.otf"), 44)

    for i in range(2):
        ry = y0 + 20 + i * ((y1 - y0 - 20) // 2)
        val = vals[i] if i < len(vals) else (35 if i == 0 else 90)
        ratio = max(0.18, min(1.0, val / vmax)) * anim
        col = sec if i == 0 else prim
        ltxt = str(lbls[i] if i < len(lbls) else f"Plano {i+1}")[:22]
        _draw_shadow_text(draw, (x0 + 18, ry), ltxt, f_lbl, (*palette["text"], int(248 * alpha_env)), anchor="lm")
        bw = max(44, int((gw - 260) * ratio))
        draw.rounded_rectangle([x0 + 18, ry + 26, x0 + gw - 210, ry + 62], radius=12, fill=(8, 12, 18, int(175 * alpha_env)))
        draw.rounded_rectangle([x0 + 18, ry + 26, x0 + 18 + bw, ry + 62], radius=12, fill=(*col, int(240 * alpha_env)))
        nums = p.get("numbers") or []
        vtxt = nums[i] if i < len(nums) else f"{int(round(val * anim))}"
        _draw_shadow_text(draw, (x0 + 36 + bw, ry + 44), vtxt[:12], f_val, (*col, int(252 * alpha_env)), anchor="lm")


def comp_process_transformation(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    cy = (y0 + y1) // 2
    gw = x1 - x0
    lx, mx, rx = x0 + int(gw * 0.18), (x0 + x1) // 2, x0 + int(gw * 0.82)
    lbls = p.get("labels") or ["Estado Inicial", "Transformação", "Resultado"]

    for dx, dy in ((-22, -16), (14, -22), (-10, 18), (22, 12)):
        draw.rectangle([lx + dx - 14, cy + dy - 14, lx + dx + 14, cy + dy + 14], outline=(*sec, int(215 * alpha_env)), width=2)
    draw.ellipse([mx - 36, cy - 36, mx + 36, cy + 36], fill=(8, 18, 32, int(210 * alpha_env)), outline=(*prim, int(245 * alpha_env)), width=3)
    draw.arc([mx - 50, cy - 50, mx + 50, cy + 50], start=int(t_sec * 160), end=int(t_sec * 160) + 120, fill=(*sec, int(235 * alpha_env)), width=4)

    faces = build_octahedron_mesh(0.55, color=prim, metallic=True)
    render_3d_faces(draw, faces, rx, cy, scale=86, rx=0.25, ry=t_sec * 1.1, rz=0.1, alpha_env=alpha_env)

    draw.line([(lx + 44, cy), (rx - 52, cy)], fill=(*prim, int(115 * alpha_env)), width=3)
    for k in range(4):
        u = (anim * 0.8 + k * 0.25 + t_sec * 0.5) % 1.0
        px = int((lx + 44) + (rx - 52 - (lx + 44)) * u)
        draw.ellipse([px - 7, cy - 7, px + 7, cy + 7], fill=(255, 255, 255, int(250 * alpha_env)))

    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
    _draw_compact_tag(draw, lx, cy + 68, str(lbls[0])[:18], f_sm, palette, alpha_env, accent_border=False)
    _draw_compact_tag(draw, rx, cy + 68, str(lbls[-1])[:18], f_sm, palette, alpha_env, accent_border=True)


def comp_calligraphy_sheet(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    cy = (y0 + y1) // 2
    for ln in (-1, 0, 1):
        ly = cy + ln * 46
        draw.line([(x0 + 24, ly), (x1 - 24, ly)], fill=(*sec, int(90 * alpha_env)), width=1)
    pts = []
    for si in range(max(2, int(44 * anim))):
        u = si / 43.0
        pts.append((x0 + 30 + int((x1 - x0 - 60) * u), cy - int(62 * math.sin(u * math.pi * 3.0) * math.exp(-0.18 * u) + 14 * math.cos(u * math.pi * 5.0))))
    if len(pts) >= 2:
        draw.line(pts, fill=(*prim, int(252 * alpha_env)), width=10, joint="curve")
        tx, ty = pts[-1]
        draw.polygon([(tx, ty), (tx + 18, ty - 44), (tx + 68, ty - 98), (tx + 86, ty - 80), (tx + 34, ty - 24)], fill=(*sec, int(248 * alpha_env)), outline=(*prim, int(252 * alpha_env)))
        draw.ellipse([tx - 7, ty - 7, tx + 7, ty + 7], fill=(255, 255, 255, int(255 * alpha_env)))


def comp_kinetic_headline(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """High-hierarchy typographic lockup (small lead + oversized accent hero + tight insight tag)."""
    x0, y0, x1, y1 = [int(v) for v in box]
    sz = int(p.get("size", 56))
    f_head = load_font(palette.get("headline_font", "CreatoDisplay-ExtraBold.otf"), sz)
    f_acc = load_font(palette.get("accent_font", "AppleGaramond-BoldItalic.ttf"), int(sz * 1.12))
    f_sub = load_font(palette.get("body_font", "DMSans.ttf"), 24)
    anim = ease(min(1.0, prog / 0.45), "cubic-out")
    fa = int(252 * alpha_env)

    title = str(p.get("title") or "").strip()
    acc = str(p.get("accent") or "").strip()
    sub = str(p.get("subtitle") or "").strip()
    centered = bool(p.get("centered", False))
    anchor = "mm" if centered else "lm"
    tx = (x0 + x1) // 2 if centered else (x0 + int((1.0 - anim) * -28))

    if centered:
        _draw_shadow_text(draw, (tx, y0 + 28), title, f_head, (*palette["text"], fa), anchor="mm")
        cy_sub = y0 + 82
        if acc:
            _draw_shadow_text(draw, (tx, y0 + 86), acc, f_acc, (*palette["primary"], fa), anchor="mm")
            cy_sub = y0 + 142
        if sub:
            _draw_shadow_text(draw, (tx, cy_sub), sub[:36], f_sub, (*palette["muted"], fa), anchor="mm")
    else:
        _draw_shadow_text(draw, (tx, y0 + 28), title, f_head, (*palette["text"], fa), anchor="lm")
        cy_sub = y0 + 74
        if acc:
            bb = draw.textbbox((tx, y0 + 28), title, font=f_head, anchor="lm")
            acc_bb = draw.textbbox((0, 0), acc, font=f_acc)
            if bb[2] + 18 + (acc_bb[2] - acc_bb[0]) <= x1:
                _draw_shadow_text(draw, (bb[2] + 16, y0 + 30), acc, f_acc, (*palette["primary"], fa), anchor="lm")
            else:
                _draw_shadow_text(draw, (tx, y0 + 82), acc, f_acc, (*palette["primary"], fa), anchor="lm")
                cy_sub = y0 + 124
        if sub:
            _draw_shadow_text(draw, (x0, cy_sub), sub[:36], f_sub, (*palette["muted"], fa), anchor="lm")
