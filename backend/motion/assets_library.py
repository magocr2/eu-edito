"""
Modular Visual Assets Library — Frameless Floating 3D, Editorial, Geo, Mechanical,
Scientific & Kinetic Typography Components (Zero Giant Slide Rectangles!).
"""
import math
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
    for fb in ("CreatoDisplay-Bold.otf", "DMSans.ttf", "BebasNeue-Regular.ttf"):
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
# FRAMELESS AMBIENT SCRIMS & SHADOW TYPOGRAPHY (ZERO SLIDE RECTANGLES!)
# ---------------------------------------------------------------------------

def draw_scene_backdrop(img: Image.Image, box: tuple, surface_mode: str, palette: dict, alpha_env: float):
    """
    Create organic feathered radial scrims + crisp minimal architectural accents
    with ZERO giant rectangular slide sheets obscuring the video.
    """
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    bg = palette["bg"]

    # Soft feathered radial depth shadow strictly inset >= 10% inside canvas edges so alpha -> 0 cleanly
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pad_x = max(110, (x1 - x0) // 9)
    pad_y = max(84, (y1 - y0) // 7)
    gd.ellipse([x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y], fill=(*bg, int(195 * alpha_env)))
    gd.ellipse([x0 + pad_x + 30, y0 + pad_y + 10, x0 + (x1 - x0) // 2 + 40, y1 - pad_y - 10], fill=(*prim, int(52 * alpha_env)))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=42)))

    draw = ImageDraw.Draw(img, "RGBA")
    # Delicate non-boxy structural cues per art direction
    if surface_mode == "scrim_brackets":
        L = 24
        ca = int(210 * alpha_env)
        for cx, cy, dx, dy in ((x0 + 36, y0 + 28, 1, 1), (x1 - 36, y0 + 28, -1, 1), (x0 + 36, y1 - 28, 1, -1), (x1 - 36, y1 - 28, -1, -1)):
            draw.line([(cx, cy), (cx + dx * L, cy)], fill=(*prim, ca), width=3)
            draw.line([(cx, cy), (cx, cy + dy * L)], fill=(*prim, ca), width=3)
    elif surface_mode == "swiss_pillar":
        draw.line([(x0 + 48, y0 + 36), (x0 + 48, y1 - 36)], fill=(*prim, int(235 * alpha_env)), width=6)
    elif surface_mode == "hairline_floating":
        draw.line([(x0 + 54, y0 + 26), (x1 - 54, y0 + 26)], fill=(*prim, int(170 * alpha_env)), width=2)
    elif surface_mode == "chronicle_rule":
        draw.line([(x0 + 54, y0 + 26), (x1 - 54, y0 + 26)], fill=(*prim, int(150 * alpha_env)), width=2)
        draw.line([(x0 + 54, y1 - 26), (x1 - 54, y1 - 26)], fill=(*prim, int(100 * alpha_env)), width=1)


def _draw_shadow_text(draw: ImageDraw.ImageDraw, pos: tuple, txt: str, font, fill: tuple, anchor: str = "lm", shadow_a: int = 200):
    x, y = int(pos[0]), int(pos[1])
    draw.text((x + 3, y + 4), txt, font=font, fill=(0, 0, 0, shadow_a), anchor=anchor)
    draw.text((x, y), txt, font=font, fill=fill, anchor=anchor)


def _draw_compact_tag(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str, font, palette: dict, alpha_env: float, accent_border: bool = True):
    """Compact sleek badge strictly wrapping label width — never a wide blank box."""
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    px, py = max(20, tw // 2 + 22), max(16, th // 2 + 12)
    prim = palette["primary"]
    bg = palette["bg"]
    draw.rounded_rectangle([cx - px, cy - py, cx + px, cy + py], radius=py, fill=(*bg, int(218 * alpha_env)), outline=(*prim, int((195 if accent_border else 80) * alpha_env)), width=2)
    draw.text((cx, cy), text, font=font, fill=(*palette["text"], int(250 * alpha_env)), anchor="mm")


# ---------------------------------------------------------------------------
# MODULAR DOMAIN COMPONENTS
# ---------------------------------------------------------------------------

def comp_3d_coins_growth(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """3D rotating metallic coin columns with contact floor shadows, glow spline, and threshold."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.72), "spring")
    gw, gh = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 10

    # Threshold beam across horizon
    hy = y0 + int(gh * 0.36)
    draw.line([(x0 + 18, hy), (x1 - 18, hy)], fill=(*prim, int(170 * alpha_env)), width=2)
    thresh_lbl = p.get("threshold_label") or ""
    if thresh_lbl:
        f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 24)
        _draw_compact_tag(draw, x0 + 115, hy - 22, thresh_lbl[:18], f_sm, palette, alpha_env)

    # Soft contact shadows on stage floor
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
    """3D rising volumetric monoliths with illuminated peak callout & contact shadows."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
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

    # Peak metric floating badge
    nums = p.get("numbers") or []
    if nums:
        f_num = load_font(palette.get("headline_font", "BebasNeue-Regular.ttf"), 42)
        _draw_compact_tag(draw, x1 - 95, y0 + 36, nums[0][:10], f_num, palette, alpha_env)


def comp_tactical_radar(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Circular tactical perimeter disk floating cleanly with radar sweep & converging units."""
    x0, y0, x1, y1 = [int(v) for v in box]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    rad = min(x1 - x0, y1 - y0) // 2 - 12
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "cubic-out")

    # Dark tactical radar circular glass disk (NO square backdrop)
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
    """Frameless curved meridian atlas grid with animated glowing trajectories & beacon pins."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    gw, gh = x1 - x0, y1 - y0

    # Curved subtle latitude arcs in open video space (zero solid square boxes!)
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
    """High-craft beveled gears + cutaway pressure chamber + torque vectors floating cleanly."""
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
        # Inner spokes
        for sp in range(3):
            sa = rot_rad + sp * (2 * math.pi / 3.0)
            draw.line([(gcx + r * 0.28 * math.cos(sa), gcy + r * 0.28 * math.sin(sa)), (gcx + r * 0.58 * math.cos(sa), gcy + r * 0.58 * math.sin(sa))], fill=(*col, int(210 * alpha_env)), width=4)

    g1x, g1y, r1 = x0 + int(gw * 0.22), cy, min(gh * 0.40, gw * 0.16)
    g2x, g2y, r2 = g1x + int(r1 * 1.66), cy - int(r1 * 0.22), r1 * 0.72
    rot1 = t_sec * 1.45
    rot2 = -rot1 * (10.0 / 7.0) + 0.22
    _draw_pro_gear(g1x, g1y, r1, 10, rot1, prim)
    _draw_pro_gear(g2x, g2y, r2, 7, rot2, sec)

    # Glass cutaway pressure cylinder & oscillating flow chamber
    px_base = g2x + int(r2 * 0.85) + 28
    chamber_x1 = min(x1 - 16, px_base + int(gw * 0.38))
    stroke = int(26 * math.sin(t_sec * 4.0))
    draw.rounded_rectangle([px_base, cy - 42, chamber_x1, cy + 42], radius=14, fill=(8, 22, 42, int(205 * alpha_env)), outline=(*prim, int(225 * alpha_env)), width=3)
    crank_x = g2x + int(r2 * 0.44 * math.cos(rot2))
    crank_y = g2y + int(r2 * 0.44 * math.sin(rot2))
    phead_x = px_base + 54 + stroke
    draw.line([(crank_x, crank_y), (phead_x, cy)], fill=(*sec, int(245 * alpha_env)), width=7)
    draw.rounded_rectangle([phead_x - 16, cy - 32, phead_x + 16, cy + 32], radius=6, fill=(*sec, int(235 * alpha_env)), outline=(255, 255, 255, int(220 * alpha_env)), width=2)
    # Chamber pressure wave on right side of piston
    if chamber_x1 - (phead_x + 22) > 20:
        draw.rounded_rectangle([phead_x + 20, cy - 30, chamber_x1 - 8, cy + 30], radius=8, fill=(*prim, int(85 * alpha_env)))

    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
    for lx, ltxt in ((g1x, "Torque"), (g2x, "Transmissão"), ((px_base + chamber_x1) // 2, "Pressão")):
        _draw_shadow_text(draw, (lx, y1 - 14), ltxt, f_sm, (*palette["text"], int(245 * alpha_env)), anchor="mb")


def comp_science_orbital(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Volumetric Bohr atom & modulated wave spectrum floating in open space."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    gw, gh = x1 - x0, y1 - y0
    acx, acy = x0 + int(gw * 0.28), (y0 + y1) // 2
    rad = int(min(gw * 0.24, gh * 0.42))

    # Nucleus & tilted orbits
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

    # Energy emission bridge + modulated harmonic wave on right
    wx0, wx1 = x0 + int(gw * 0.56), x1 - 24
    wy_mid = (y0 + y1) // 2
    wave_pts = []
    for i in range(40):
        u = i / 39.0
        wave_pts.append((wx0 + int((wx1 - wx0) * u), wy_mid + int(56 * math.sin(u * math.pi * 4.5 - t_sec * 5.2) * math.sin(u * math.pi))))
    draw.line(wave_pts, fill=(*sec, int(248 * alpha_env)), width=6, joint="curve")
    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 22)
    _draw_compact_tag(draw, (wx0 + wx1) // 2, y1 - 24, "ÓRBITA • ONDA • ENERGIA", f_sm, palette, alpha_env, accent_border=False)


def comp_ai_neural_architecture(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Rotating 3D crystal octahedron core + animated neon neural routing signals."""
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
    """Frameless luminous timeline ribbon with large engraved year medallions."""
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
    """Frameless Dual Proportional Comparison Bars + Glowing Center Divider (Zero white slide!)."""
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
        # Dark glass track + glowing filled bar
        draw.rounded_rectangle([x0 + 18, ry + 26, x0 + gw - 210, ry + 62], radius=12, fill=(8, 12, 18, int(175 * alpha_env)))
        draw.rounded_rectangle([x0 + 18, ry + 26, x0 + 18 + bw, ry + 62], radius=12, fill=(*col, int(240 * alpha_env)))
        nums = p.get("numbers") or []
        vtxt = nums[i] if i < len(nums) else f"{int(round(val * anim))}"
        _draw_shadow_text(draw, (x0 + 36 + bw, ry + 44), vtxt[:12], f_val, (*col, int(252 * alpha_env)), anchor="lm")


def comp_process_transformation(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Multi-node particle catalytic stream transforming raw cluster into crystalline emblem."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    cy = (y0 + y1) // 2
    gw = x1 - x0
    lx, mx, rx = x0 + int(gw * 0.18), (x0 + x1) // 2, x0 + int(gw * 0.82)
    lbls = p.get("labels") or ["Estado Inicial", "Transformação", "Resultado"]

    # Raw fractured cluster on left
    for dx, dy in ((-22, -16), (14, -22), (-10, 18), (22, 12)):
        draw.rectangle([lx + dx - 14, cy + dy - 14, lx + dx + 14, cy + dy + 14], outline=(*sec, int(215 * alpha_env)), width=2)

    # Central catalytic lens ring spinning dynamically
    draw.ellipse([mx - 36, cy - 36, mx + 36, cy + 36], fill=(8, 18, 32, int(210 * alpha_env)), outline=(*prim, int(245 * alpha_env)), width=3)
    draw.arc([mx - 50, cy - 50, mx + 50, cy + 50], start=int(t_sec * 160), end=int(t_sec * 160) + 120, fill=(*sec, int(235 * alpha_env)), width=4)

    # Evolved glowing crystal emblem on right
    faces = build_octahedron_mesh(0.55, color=prim, metallic=True)
    render_3d_faces(draw, faces, rx, cy, scale=86, rx=0.25, ry=t_sec * 1.1, rz=0.1, alpha_env=alpha_env)

    # Flowing energy particles traversing lx -> mx -> rx
    draw.line([(lx + 44, cy), (rx - 52, cy)], fill=(*prim, int(115 * alpha_env)), width=3)
    for k in range(4):
        u = (anim * 0.8 + k * 0.25 + t_sec * 0.5) % 1.0
        px = int((lx + 44) + (rx - 52 - (lx + 44)) * u)
        draw.ellipse([px - 7, cy - 7, px + 7, cy + 7], fill=(255, 255, 255, int(250 * alpha_env)))

    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
    _draw_compact_tag(draw, lx, cy + 68, str(lbls[0])[:18], f_sm, palette, alpha_env, accent_border=False)
    _draw_compact_tag(draw, rx, cy + 68, str(lbls[-1])[:18], f_sm, palette, alpha_env, accent_border=True)


def comp_calligraphy_sheet(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Floating cream calligraphy sheet with live fountain pen drawing luminous cursive strokes."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    draw.rounded_rectangle([x0 + 14, y0 + 10, x1 - 14, y1 - 10], radius=18, fill=(252, 249, 242, int(242 * alpha_env)), outline=(*prim, int(215 * alpha_env)), width=3)
    for ln in range(3):
        ly = y0 + 54 + ln * 56
        draw.line([(x0 + 40, ly), (x1 - 40, ly)], fill=(148, 163, 184, int(150 * alpha_env)), width=2)
    pts = []
    for si in range(max(2, int(40 * anim))):
        u = si / 39.0
        pts.append((x0 + 48 + int((x1 - x0 - 96) * u), y0 + 130 - int(46 * math.sin(u * math.pi * 3.0) * math.exp(-0.2 * u))))
    if len(pts) >= 2:
        draw.line(pts, fill=(*prim, int(250 * alpha_env)), width=8, joint="curve")
        tx, ty = pts[-1]
        draw.polygon([(tx, ty), (tx + 16, ty - 38), (tx + 58, ty - 84), (tx + 72, ty - 70), (tx + 30, ty - 20)], fill=(15, 23, 42, int(245 * alpha_env)))
        draw.ellipse([tx - 6, ty - 6, tx + 6, ty + 6], fill=(*prim, int(255 * alpha_env)))


def comp_kinetic_headline(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """High-hierarchy typographic lockup with drop shadow, mixed Sans+Serif Italic & concise insight tag."""
    x0, y0, x1, y1 = [int(v) for v in box]
    f_head = load_font(palette.get("headline_font", "CreatoDisplay-ExtraBold.otf"), int(p.get("size", 54)))
    f_acc = load_font(palette.get("accent_font", "AppleGaramond-BoldItalic.ttf"), int(p.get("size", 54)))
    f_sub = load_font(palette.get("body_font", "DMSans.ttf"), 24)
    anim = ease(min(1.0, prog / 0.45), "cubic-out")
    fa = int(252 * alpha_env)

    title = str(p.get("title") or "").strip()
    acc = str(p.get("accent") or "").strip()
    sub = str(p.get("subtitle") or "").strip()

    dx = int((1.0 - anim) * -28)
    _draw_shadow_text(draw, (x0 + dx, y0 + 28), title, f_head, (*palette["text"], fa), anchor="lm")
    cy_sub = y0 + 74
    if acc:
        bb = draw.textbbox((x0 + dx, y0 + 28), title, font=f_head, anchor="lm")
        acc_bb = draw.textbbox((0, 0), acc, font=f_acc)
        acc_w = acc_bb[2] - acc_bb[0]
        if bb[2] + 18 + acc_w <= x1:
            _draw_shadow_text(draw, (bb[2] + 16, y0 + 30), acc, f_acc, (*palette["primary"], fa), anchor="lm")
        else:
            _draw_shadow_text(draw, (x0 + dx, y0 + 78), acc, f_acc, (*palette["primary"], fa), anchor="lm")
            cy_sub = y0 + 118
    if sub:
        _draw_shadow_text(draw, (x0, cy_sub), sub[:36], f_sub, (*palette["muted"], fa), anchor="lm")
