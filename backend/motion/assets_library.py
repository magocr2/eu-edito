"""
Modular Visual Assets Library (3D Projected Meshes, Geo, Tech, Mechanical, Science, Editorial)
Provides reusable, parameterized graphical components — NEVER fixed final templates.
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
# TRUE 3D PERSPECTIVE MESH ENGINE (Key/Rim Lit Polygons with Z-Sort)
# ---------------------------------------------------------------------------

def render_3d_faces(draw: ImageDraw.ImageDraw, faces: list, cx: int, cy: int, scale: float, rx: float, ry: float, rz: float, alpha_env: float, light_dir=(0.45, -0.70, 0.55), fov: float = 4.2):
    """
    Project 3D quad/tri faces with Euler rotation, perspective projection,
    Painter's algorithm depth sort, and directional + rim lighting.
    faces = [([v0, v1, v2, ...], base_rgb, is_metallic), ...]
    """
    ld = _v_norm(light_dir)
    view_dir = (0.0, 0.0, 1.0)
    projected = []
    for verts, base_rgb, metallic in faces:
        rverts = [_rot_pt(v, rx, ry, rz) for v in verts]
        if len(rverts) < 3:
            continue
        n = _v_norm(_v_cross(_v_sub(rverts[1], rverts[0]), _v_sub(rverts[2], rverts[0])))
        # Keep double-sided slight shading if thin, or illuminate nicely
        ndotl = max(0.18, abs(_v_dot(n, ld)))
        spec = 0.0
        if metallic:
            hv = _v_norm((ld[0] + view_dir[0], ld[1] + view_dir[1], ld[2] + view_dir[2]))
            spec = pow(max(0.0, abs(_v_dot(n, hv))), 14.0) * 110.0
        avg_z = sum(v[2] for v in rverts) / float(len(rverts))
        pts2d = []
        for x, y, z in rverts:
            persp = fov / max(1.2, fov - z)
            pts2d.append((cx + x * scale * persp, cy + y * scale * persp))
        lit_rgb = clamp_rgb(base_rgb, 0.42 + 0.68 * ndotl, spec)
        edge_rgb = clamp_rgb(base_rgb, 1.15, 25)
        projected.append((avg_z, pts2d, lit_rgb, edge_rgb))

    projected.sort(key=lambda item: item[0])
    a = int(246 * alpha_env)
    ea = int(175 * alpha_env)
    for _, pts2d, fill_c, edge_c in projected:
        draw.polygon(pts2d, fill=(*fill_c, a), outline=(*edge_c, ea))


def build_box_mesh(w: float, h: float, d: float, offset=(0.0, 0.0, 0.0), color=(250, 204, 21), metallic=True):
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
    faces = [(top_ring, clamp_rgb(color, 1.08, 12), metallic), (list(reversed(bot_ring)), clamp_rgb(color, 0.72), metallic)]
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
# STRUCTURAL ART-STYLE SURFACES (Adapts surface look by Art Direction!)
# ---------------------------------------------------------------------------

def draw_scene_backdrop(img: Image.Image, box: tuple, border_style: str, palette: dict, alpha_env: float):
    """Draw the tailored art-direction surface (paper, tactical brackets, blueprint grid, or halo) — NEVER generic cards."""
    x0, y0, x1, y1 = [int(v) for v in box]
    draw = ImageDraw.Draw(img, "RGBA")
    surf = palette["surface"]
    prim = palette["primary"]
    sec = palette["secondary"]
    sa = int(palette.get("surface_alpha", 215) * alpha_env)

    if border_style == "frameless_halo":
        # Inset blur margin (>= 84px inside canvas edges) so glow reaches alpha=0 cleanly with zero rectangle seam
        glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        pad_x = max(88, (x1 - x0) // 10)
        pad_y = max(76, (y1 - y0) // 8)
        gd.ellipse([x0 + pad_x, y0 + pad_y, x1 - pad_x, y1 - pad_y], fill=(*palette["bg"], int(210 * alpha_env)))
        gd.ellipse([x0 + pad_x + 20, y0 + pad_y, x0 + (x1 - x0) // 2, y1 - pad_y], fill=(*prim, int(58 * alpha_env)))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=36)))
        return

    # Subtle drop shadow
    draw.rectangle([x0 + 6, y0 + 8, x1 + 6, y1 + 10], fill=(0, 0, 0, int(90 * alpha_env)))
    draw.rectangle([x0, y0, x1, y1], fill=(*surf, sa))

    if border_style == "brackets":
        # Tactical corner HUD brackets + fine reticle ticks
        L = 28
        ca = int(230 * alpha_env)
        for cx, cy, dx, dy in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
            draw.line([(cx, cy), (cx + dx * L, cy)], fill=(*prim, ca), width=4)
            draw.line([(cx, cy), (cx, cy + dy * L)], fill=(*prim, ca), width=4)
        draw.line([(x0, y0 + 54), (x1, y0 + 54)], fill=(*prim, int(80 * alpha_env)), width=1)

    elif border_style == "hairline_rule":
        # High-contrast magazine broadsheet rules
        draw.line([(x0, y0), (x1, y0)], fill=(*sec, int(230 * alpha_env)), width=5)
        draw.line([(x0, y0 + 9), (x1, y0 + 9)], fill=(*prim, int(220 * alpha_env)), width=2)
        draw.line([(x0, y1), (x1, y1)], fill=(*sec, int(190 * alpha_env)), width=2)

    elif border_style == "crosshair_grid":
        # Technical blueprint subtle coordinate grid
        ga = int(42 * alpha_env)
        for gx in range(x0 + 48, x1, 56):
            draw.line([(gx, y0), (gx, y1)], fill=(*prim, ga), width=1)
        for gy in range(y0 + 48, y1, 56):
            draw.line([(x0, gy), (x1, gy)], fill=(*prim, ga), width=1)
        draw.rectangle([x0, y0, x1, y1], outline=(*prim, int(165 * alpha_env)), width=2)

    elif border_style == "meridian_frame":
        draw.rectangle([x0, y0, x1, y1], outline=(*sec, int(130 * alpha_env)), width=2)
        draw.rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], outline=(*prim, int(85 * alpha_env)), width=1)

    elif border_style == "editorial_ticks":
        # Archival documentary double rule
        draw.rectangle([x0, y0, x1, y1], outline=(*prim, int(170 * alpha_env)), width=3)
        draw.line([(x0 + 24, y0 + 18), (x1 - 24, y0 + 18)], fill=(*sec, int(150 * alpha_env)), width=2)

    elif border_style == "swiss_bar":
        # Clean left electric color accent pillar
        draw.rectangle([x0, y0, x0 + 14, y1], fill=(*prim, int(245 * alpha_env)))
        draw.line([(x0 + 14, y1), (x1, y1)], fill=(*sec, int(80 * alpha_env)), width=2)

    else:
        draw.rectangle([x0, y0, x1, y1], outline=(*prim, int(140 * alpha_env)), width=2)


# ---------------------------------------------------------------------------
# MODULAR DOMAIN COMPONENTS
# ---------------------------------------------------------------------------

def comp_3d_coins_growth(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """3D rotating stacked metallic coins ascending across threshold horizon."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.72), "spring")

    # Threshold horizon line (e.g. R$ 10 MIL)
    hy = y0 + int((y1 - y0) * 0.42)
    draw.line([(x0, hy), (x1, hy)], fill=(*prim, int(130 * alpha_env)), width=2)
    thresh_lbl = p.get("threshold_label") or ""
    if thresh_lbl:
        f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 24)
        draw.text((x0 + 12, hy - 14), thresh_lbl[:18], font=f_sm, fill=(*prim, int(240 * alpha_env)), anchor="lb")

    # 3 ascending 3D coin stacks
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
    render_3d_faces(draw, faces, (x0 + x1) // 2, (y0 + y1) // 2 + 12, scale=(x1 - x0) * 0.20, rx=0.28, ry=t_sec * 0.65, rz=0.0, alpha_env=alpha_env)


def comp_3d_pillars_scale(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """3D volumetric bar monoliths + soaring trend ribbon for company scale."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.72), "cubic-out")
    vals = p.get("values") or [25, 48, 76, 100]
    vmax = max(vals) or 100.0
    faces = []
    n = min(4, len(vals))
    for i in range(n):
        h_3d = max(0.25, 1.8 * (vals[i] / vmax) * anim)
        col = prim if i == n - 1 else clamp_rgb(sec, 0.65, 40)
        faces.extend(build_box_mesh(0.46, h_3d, 0.46, offset=(-1.35 + i * 0.90, 0.95 - h_3d * 0.5, 0.0), color=col, metallic=(i == n - 1)))
    render_3d_faces(draw, faces, (x0 + x1) // 2, (y0 + y1) // 2 + 22, scale=(x1 - x0) * 0.22, rx=0.24, ry=-0.42 + math.sin(t_sec * 0.8) * 0.12, rz=0.0, alpha_env=alpha_env)


def comp_tactical_radar(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Police/Security Tactical Perimeter Map with rotating radar sweep and converging units."""
    x0, y0, x1, y1 = [int(v) for v in box]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    rad = min(x1 - x0, y1 - y0) // 2 - 14
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "cubic-out")

    # Tactical street grid
    for k in range(-2, 3):
        draw.line([(x0 + 10, cy + k * (rad // 2)), (x1 - 10, cy + k * (rad // 2))], fill=(*prim, int(45 * alpha_env)), width=1)
        draw.line([(cx + k * (rad // 2), y0 + 10), (cx + k * (rad // 2), y1 - 10)], fill=(*prim, int(45 * alpha_env)), width=1)

    # Radar range rings
    for rf in (0.38, 0.70, 0.98):
        rr = int(rad * rf)
        draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(*prim, int(130 * alpha_env)), width=2)

    # Rotating tactical radar sweep wedge
    ang_deg = int((t_sec * 110) % 360)
    draw.pieslice([cx - rad, cy - rad, cx + rad, cy + rad], start=ang_deg - 38, end=ang_deg, fill=(*prim, int(55 * alpha_env)))

    # Converging operational units moving inward toward perimeter lock!
    unit_angles = (-145, -35, 45, 145)
    raw_lbls = p.get("labels") or []
    lbls = raw_lbls if len(raw_lbls) >= 2 else ["Setor N", "Cerco L", "Base S", "Alvo"]
    for ui, ang in enumerate(unit_angles):
        dist = rad * (1.05 - 0.62 * anim)
        ux = cx + int(dist * math.cos(math.radians(ang)))
        uy = cy + int(dist * math.sin(math.radians(ang)))
        draw.line([(ux, uy), (cx, cy)], fill=(*sec, int(110 * alpha_env)), width=2)
        draw.ellipse([ux - 9, uy - 9, ux + 9, uy + 9], fill=(*sec, int(245 * alpha_env)), outline=(255, 255, 255, int(220 * alpha_env)), width=2)
        if ui < len(lbls):
            f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
            draw.text((ux, uy - 18), lbls[ui][:12], font=f_sm, fill=(*palette["text"], int(240 * alpha_env)), anchor="mb")

    # Central lock reticle
    pulse = 16 + int(8 * abs(math.sin(t_sec * 5.0)))
    draw.ellipse([cx - pulse, cy - pulse, cx + pulse, cy + pulse], outline=(*sec, int(235 * alpha_env)), width=3)
    draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(*sec, int(250 * alpha_env)))


def comp_geo_route_map(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Cartographic map with latitude/longitude meridians, landmass silhouettes, and curved trajectories."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")

    # Curved latitude arcs
    gw, gh = x1 - x0, y1 - y0
    for k in range(1, 5):
        gy = y0 + int(gh * k / 5.0)
        draw.line([(x0, gy), (x1, gy)], fill=(*sec, int(45 * alpha_env)), width=1)
        gx = x0 + int(gw * k / 5.0)
        draw.line([(gx, y0), (gx, y1)], fill=(*sec, int(45 * alpha_env)), width=1)

    # Stylized terrain contours (solid cartographic fill so backdrop alpha never turns translucent)
    land_c = clamp_rgb(sec, 0.36)
    draw.polygon([(x0 + int(gw * 0.08), y0 + int(gh * 0.20)), (x0 + int(gw * 0.42), y0 + int(gh * 0.14)), (x0 + int(gw * 0.48), y0 + int(gh * 0.80)), (x0 + int(gw * 0.14), y0 + int(gh * 0.76))], fill=(*land_c, int(210 * alpha_env)), outline=(*sec, int(140 * alpha_env)))
    draw.polygon([(x0 + int(gw * 0.54), y0 + int(gh * 0.28)), (x0 + int(gw * 0.90), y0 + int(gh * 0.18)), (x0 + int(gw * 0.86), y0 + int(gh * 0.82)), (x0 + int(gw * 0.58), y0 + int(gh * 0.72))], fill=(*land_c, int(210 * alpha_env)), outline=(*sec, int(140 * alpha_env)))

    places = p.get("labels") or ["Origem", "Escala", "Destino"]
    n_pins = max(2, min(4, len(places)))
    pts = [
        (x0 + int(gw * (0.16 + 0.68 * i / float(max(1, n_pins - 1)))), y0 + int(gh * (0.64 if i % 2 == 0 else 0.30)))
        for i in range(n_pins)
    ]

    for i in range(n_pins - 1):
        p0, p1 = pts[i], pts[i + 1]
        apts = []
        steps = 26
        max_s = max(2, int(steps * anim))
        for si in range(max_s):
            u = si / float(steps - 1)
            apts.append((int(p0[0] + (p1[0] - p0[0]) * u), int(p0[1] + (p1[1] - p0[1]) * u - 54 * math.sin(math.pi * u))))
        if len(apts) >= 2:
            draw.line(apts, fill=(*prim, int(245 * alpha_env)), width=6)
            hx, hy = apts[-1]
            draw.ellipse([hx - 8, hy - 8, hx + 8, hy + 8], fill=(255, 255, 255, int(250 * alpha_env)))

    f_lbl = load_font(palette.get("body_font", "DMSans.ttf"), 22)
    for i, (px, py) in enumerate(pts):
        pulse = 14 + int(8 * abs(math.sin(t_sec * 4.2 + i)))
        draw.ellipse([px - pulse, py - pulse, px + pulse, py + pulse], outline=(*prim, int(150 * alpha_env)), width=2)
        draw.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(*prim, int(250 * alpha_env)), outline=(255, 255, 255, int(250 * alpha_env)), width=2)
        draw.rectangle([px - 70, py + 16, px + 70, py + 48], fill=(*palette["bg"], int(225 * alpha_env)), outline=(*prim, int(170 * alpha_env)), width=1)
        draw.text((px, py + 32), str(places[i])[:14], font=f_lbl, fill=(*palette["text"], int(250 * alpha_env)), anchor="mm")


def comp_machine_cutaway(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Synchronized meshed gears + reciprocating piston cutaway with energy flow arrows."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    gw, gh = x1 - x0, y1 - y0
    cy = (y0 + y1) // 2

    def _draw_gear(gcx, gcy, r, teeth, rot_rad, col):
        pts = []
        for k in range(teeth * 2):
            a = rot_rad + (k * math.pi) / teeth
            rr = r if k % 2 == 0 else r * 0.78
            pts.append((gcx + rr * math.cos(a), gcy + rr * math.sin(a)))
        draw.polygon(pts, fill=(*col, int(72 * alpha_env)), outline=(*col, int(245 * alpha_env)))
        draw.ellipse([gcx - r * 0.32, gcy - r * 0.32, gcx + r * 0.32, gcy + r * 0.32], fill=(*palette["bg"], int(235 * alpha_env)), outline=(*col, int(245 * alpha_env)), width=3)

    # Intermeshed primary (10 teeth) & secondary (7 teeth) gears spinning continuously
    g1x, g1y, r1 = x0 + int(gw * 0.26), cy, min(gh * 0.38, gw * 0.16)
    g2x, g2y, r2 = g1x + int(r1 * 1.68), cy - int(r1 * 0.25), r1 * 0.72
    rot1 = t_sec * 1.4
    rot2 = -rot1 * (10.0 / 7.0) + 0.22
    _draw_gear(g1x, g1y, r1, 10, rot1, prim)
    _draw_gear(g2x, g2y, r2, 7, rot2, sec)

    # Connecting rod + reciprocating piston chamber on right!
    px_base = g2x + int(r2 * 0.85) + 34
    chamber_x1 = min(x1 - 24, px_base + int(gw * 0.34))
    stroke = int(26 * math.sin(t_sec * 3.8))
    # Cylinder housing
    draw.rectangle([px_base, cy - 46, chamber_x1, cy + 46], outline=(*prim, int(195 * alpha_env)), width=3)
    # Moving piston head + connecting crank pin
    crank_x = g2x + int(r2 * 0.45 * math.cos(rot2))
    crank_y = g2y + int(r2 * 0.45 * math.sin(rot2))
    phead_x = px_base + 54 + stroke
    draw.line([(crank_x, crank_y), (phead_x, cy)], fill=(*sec, int(235 * alpha_env)), width=7)
    draw.rectangle([phead_x - 16, cy - 36, phead_x + 16, cy + 36], fill=(*sec, int(220 * alpha_env)), outline=(255, 255, 255, int(200 * alpha_env)), width=2)

    lbls = p.get("labels") or ["Entrada", "Transmissão", "Força"]
    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 20)
    for lx, ltxt in ((g1x, lbls[0] if lbls else "Torque"), (g2x, lbls[1] if len(lbls) > 1 else "Eixo"), ((px_base + chamber_x1) // 2, lbls[2] if len(lbls) > 2 else "Pressão")):
        draw.text((lx, y1 - 16), ltxt[:14], font=f_sm, fill=(*palette["text"], int(230 * alpha_env)), anchor="mb")


def comp_science_orbital(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Bohr atomic / scientific wave phenomenon with glowing tilted orbits and oscilloscope spectrum."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    gw, gh = x1 - x0, y1 - y0
    acx, acy = x0 + int(gw * 0.30), (y0 + y1) // 2
    rad = int(min(gw * 0.24, gh * 0.40))

    # Central nucleus
    draw.ellipse([acx - 20, acy - 20, acx + 20, acy + 20], fill=(*sec, int(245 * alpha_env)), outline=(255, 255, 255, int(220 * alpha_env)), width=3)

    # 3 tilted elliptical orbital paths + orbiting particles
    for oi, tilt in enumerate((0.2, 1.25, 2.3)):
        op_pts = []
        for s in range(44):
            a = 2 * math.pi * s / 43.0
            ox_l = rad * math.cos(a)
            oy_l = rad * 0.42 * math.sin(a)
            rx = acx + ox_l * math.cos(tilt) - oy_l * math.sin(tilt)
            ry = acy + ox_l * math.sin(tilt) + oy_l * math.cos(tilt)
            op_pts.append((rx, ry))
        draw.line(op_pts, fill=(*prim, int(145 * alpha_env)), width=2)
        pa = t_sec * (2.2 + oi * 0.6) + oi * 2.1
        px = acx + (rad * math.cos(pa)) * math.cos(tilt) - (rad * 0.42 * math.sin(pa)) * math.sin(tilt)
        py = acy + (rad * math.cos(pa)) * math.sin(tilt) + (rad * 0.42 * math.sin(pa)) * math.cos(tilt)
        draw.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(*sec, int(250 * alpha_env)))

    # Right side scientific wave spectrum / readout
    wx0, wx1 = x0 + int(gw * 0.56), x1 - 24
    wy_mid = (y0 + y1) // 2
    wave_pts = []
    for i in range(36):
        u = i / 35.0
        wx = wx0 + int((wx1 - wx0) * u)
        wy = wy_mid + int(54 * math.sin(u * math.pi * 4.0 - t_sec * 5.0) * math.sin(u * math.pi))
        wave_pts.append((wx, wy))
    draw.line(wave_pts, fill=(*sec, int(245 * alpha_env)), width=5, joint="curve")
    lbls = p.get("labels") or ["Núcleo", "Órbita", "Energia"]
    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 22)
    draw.text(((wx0 + wx1) // 2, y1 - 22), "  •  ".join(str(l)[:12] for l in lbls[:3]), font=f_sm, fill=(*palette["text"], int(235 * alpha_env)), anchor="mb")


def comp_ai_neural_architecture(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """3D crystalline processing octahedron + animated PCB routing signals."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    gw = x1 - x0
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2

    # Left-to-right circuit routing lines feeding center 3D core
    node_ys = (y0 + 38, cy, y1 - 38)
    for ni, ny in enumerate(node_ys):
        lx0 = x0 + 36
        rx1 = x1 - 36
        draw.line([(lx0, ny), (cx - 86, cy)], fill=(*prim, int(110 * alpha_env)), width=3)
        draw.line([(cx + 86, cy), (rx1, ny)], fill=(*sec, int(110 * alpha_env)), width=3)
        pulse_u = (t_sec * 1.1 + ni * 0.33) % 1.0
        px = int(lx0 + (cx - 86 - lx0) * pulse_u)
        py = int(ny + (cy - ny) * pulse_u)
        draw.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(255, 255, 255, int(245 * alpha_env)))
        draw.ellipse([lx0 - 10, ny - 10, lx0 + 10, ny + 10], fill=(*prim, int(230 * alpha_env)))
        draw.ellipse([rx1 - 10, ny - 10, rx1 + 10, ny + 10], fill=(*sec, int(230 * alpha_env)))

    # 3D rotating crystal AI core in center
    faces = build_octahedron_mesh(0.75, color=prim, metallic=True)
    render_3d_faces(draw, faces, cx, cy, scale=110, rx=0.32, ry=t_sec * 1.2, rz=0.15, alpha_env=alpha_env)


def comp_chronology_archive(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Archival historical timeline ruler with documentary cards revealing chronologically."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.80), "cubic-out")
    cy = (y0 + y1) // 2 + 12

    draw.line([(x0 + 40, cy), (x1 - 40, cy)], fill=(*sec, int(110 * alpha_env)), width=4)
    draw.line([(x0 + 40, cy), (x0 + 40 + int((x1 - x0 - 80) * anim), cy)], fill=(*prim, int(240 * alpha_env)), width=5)

    items = p.get("labels") or ["Marco 1", "Virada", "Legado"]
    n = max(2, min(4, len(items)))
    f_yr = load_font(palette.get("headline_font", "AppleGaramond-BoldItalic.ttf"), 34)
    f_tx = load_font(palette.get("body_font", "DMSans.ttf"), 22)

    for i in range(n):
        ix = x0 + 90 + int(((x1 - x0 - 180) * i) / float(max(1, n - 1)))
        lit = anim >= i / float(n)
        col = prim if lit else palette["muted"]
        draw.ellipse([ix - 12, cy - 12, ix + 12, cy + 12], fill=(*col, int(245 * alpha_env)), outline=(*palette["surface"], int(240 * alpha_env)), width=3)
        dy_off = -58 if i % 2 == 0 else 58
        draw.line([(ix, cy), (ix, cy + dy_off)], fill=(*col, int(170 * alpha_env)), width=2)
        draw.text((ix, cy + dy_off + (-16 if i % 2 == 0 else 18)), str(items[i])[:18], font=f_tx if len(str(items[i])) > 6 else f_yr, fill=(*palette["text"], int(250 * alpha_env) if lit else int(120 * alpha_env)), anchor="mm")


def comp_editorial_comparison(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Editorial proportional balance / dual bar morph comparing two real figures/states."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim_raw = min(1.0, prog / 0.72)
    anim = min(1.08, ease(anim_raw, "spring"))
    anim_clamped = ease(anim_raw, "cubic-out")
    lbls = p.get("labels") or ["Cenário A", "Cenário B"]
    vals = p.get("values") or [32, 92]
    vmax = max(vals[:2] or [100]) or 100.0
    gw = x1 - x0
    f_lbl = load_font(palette.get("body_font", "DMSans.ttf"), 26)
    f_val = load_font(palette.get("headline_font", "CreatoDisplay-ExtraBold.otf"), 44)

    for i in range(2):
        ry = y0 + 26 + i * ((y1 - y0 - 40) // 2)
        val = vals[i] if i < len(vals) else (35 if i == 0 else 90)
        ratio = max(0.18, min(1.0, val / vmax)) * anim_clamped
        col = sec if i == 0 else prim
        draw.text((x0 + 18, ry), str(lbls[i] if i < len(lbls) else f"Valor {i+1}")[:26], font=f_lbl, fill=(*palette["text"], int(245 * alpha_env)), anchor="lm")
        bw = max(36, int((gw - 220) * ratio))
        draw.rectangle([x0 + 18, ry + 26, x0 + 18 + bw, ry + 62], fill=(*col, int(230 * alpha_env)))
        nums = p.get("numbers") or []
        vtxt = nums[i] if i < len(nums) else f"{int(round(val * anim_clamped))}"
        draw.text((x0 + 36 + bw, ry + 44), vtxt[:12], font=f_val, fill=(*col, int(250 * alpha_env)), anchor="lm")


def comp_process_transformation(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Dynamic state morph: State A -> Catalytic Particle Bridge -> Evolved State B."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim, sec = palette["primary"], palette["secondary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    cy = (y0 + y1) // 2
    gw = x1 - x0
    lx, rx = x0 + int(gw * 0.22), x0 + int(gw * 0.78)
    lbls = p.get("labels") or ["Estado Inicial", "Catalisador", "Resultado"]

    # State A (raw angular polygon) vs State B (polished glowing ring + octagon)
    draw.rectangle([lx - 58, cy - 48, lx + 58, cy + 48], outline=(*sec, int(195 * alpha_env)), width=3)
    draw.regular_polygon((rx, cy, 56), n_sides=8, rotation=t_sec * 18, fill=(*prim, int(68 * alpha_env)), outline=(*prim, int(245 * alpha_env)))

    # Flowing morph bridge across center
    bx_end = lx + 72 + int((rx - lx - 144) * anim)
    draw.line([(lx + 72, cy), (bx_end, cy)], fill=(*prim, int(240 * alpha_env)), width=6)
    draw.ellipse([bx_end - 11, cy - 11, bx_end + 11, cy + 11], fill=(255, 255, 255, int(250 * alpha_env)))

    f_sm = load_font(palette.get("body_font", "DMSans.ttf"), 22)
    l_txt = str(lbls[0])[:20] if lbls else "Estado Inicial"
    r_txt = str(lbls[-1])[:20] if len(lbls) >= 2 else "Resultado"
    draw.text((lx, cy + 74), l_txt, font=f_sm, fill=(*palette["text"], int(235 * alpha_env)), anchor="mm")
    draw.text((rx, cy + 74), r_txt, font=f_sm, fill=(*prim, int(250 * alpha_env)), anchor="mm")


def comp_calligraphy_sheet(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """Illustrative handwriting sheet with live pen tip drawing expressive cursive strokes."""
    x0, y0, x1, y1 = [int(v) for v in box]
    prim = palette["primary"]
    anim = ease(min(1.0, prog / 0.78), "smooth")
    draw.rectangle([x0 + 18, y0 + 10, x1 - 18, y1 - 10], fill=(252, 249, 242, int(240 * alpha_env)), outline=(*prim, int(200 * alpha_env)), width=3)
    for ln in range(3):
        ly = y0 + 54 + ln * 56
        draw.line([(x0 + 44, ly), (x1 - 44, ly)], fill=(148, 163, 184, int(145 * alpha_env)), width=2)
    pts = []
    for si in range(max(2, int(40 * anim))):
        u = si / 39.0
        pts.append((x0 + 54 + int((x1 - x0 - 108) * u), y0 + 132 - int(48 * math.sin(u * math.pi * 3.0) * math.exp(-0.2 * u))))
    if len(pts) >= 2:
        draw.line(pts, fill=(*prim, int(250 * alpha_env)), width=8, joint="curve")
        tx, ty = pts[-1]
        draw.polygon([(tx, ty), (tx + 16, ty - 38), (tx + 58, ty - 84), (tx + 72, ty - 70), (tx + 30, ty - 20)], fill=(15, 23, 42, int(245 * alpha_env)))
        draw.ellipse([tx - 6, ty - 6, tx + 6, ty + 6], fill=(*prim, int(255 * alpha_env)))


def comp_kinetic_headline(draw: ImageDraw.ImageDraw, box: tuple, p: dict, prog: float, t_sec: float, palette: dict, alpha_env: float):
    """High-hierarchy typographic lockup with progressive word reveal + accent bar."""
    x0, y0, x1, y1 = [int(v) for v in box]
    f_head = load_font(palette.get("headline_font", "CreatoDisplay-ExtraBold.otf"), int(p.get("size", 56)))
    f_acc = load_font(palette.get("accent_font", "AppleGaramond-BoldItalic.ttf"), int(p.get("size", 56)))
    f_sub = load_font(palette.get("body_font", "DMSans.ttf"), 26)
    anim = ease(min(1.0, prog / 0.45), "cubic-out")
    fa = int(252 * alpha_env)

    title = str(p.get("title") or "").strip()
    acc = str(p.get("accent") or "").strip()
    sub = str(p.get("subtitle") or "").strip()

    # Slide + mask reveal horizontally
    dx = int((1.0 - anim) * -28)
    draw.text((x0 + dx, y0 + 30), title[:28], font=f_head, fill=(*palette["text"], fa), anchor="lm")
    if acc:
        bb = draw.textbbox((x0 + dx, y0 + 30), title[:28], font=f_head, anchor="lm")
        if bb[2] + 18 + len(acc) * 18 < x1:
            draw.text((bb[2] + 16, y0 + 32), acc[:24], font=f_acc, fill=(*palette["primary"], fa), anchor="lm")
        else:
            draw.text((x0 + dx, y0 + 78), acc[:28], font=f_acc, fill=(*palette["primary"], fa), anchor="lm")
    if sub:
        sy = y0 + (116 if acc and len(title) > 15 else 78)
        draw.text((x0, sy), sub[:54], font=f_sub, fill=(*palette["muted"], fa), anchor="lm")
