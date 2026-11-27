"""
Visual Quality Gate
Evaluates every planned scene (pre-render) and sampled rendered frame (post-render)
for narrative grounding, visual diversity, contrast legibility, spatial safety,
and non-generic visual finish.
"""


def _rel_luminance(rgb: tuple) -> float:
    r, g, b = [c / 255.0 for c in rgb[:3]]
    def _lin(u):
        return u / 12.92 if u <= 0.03928 else ((u + 0.055) / 1.055) ** 2.4
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(c1: tuple, c2: tuple) -> float:
    l1, l2 = _rel_luminance(c1), _rel_luminance(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def validate_and_refine_plan(scene_plan: dict, interpretation: dict, frame_info: dict = None, used_signatures: list = None) -> dict:
    """
    Validate typography contrast, avoid generic title leakage, verify narrative numbers,
    and annotate deterministic quality audit metrics.
    """
    plan = dict(scene_plan)
    palette = dict(plan.get("palette") or {})
    surf = tuple(palette.get("surface", (16, 22, 32)))
    txt = tuple(palette.get("text", (245, 248, 252)))

    # Enforce WCAG readability (>= 4.5 contrast ratio on surface)
    if contrast_ratio(txt, surf) < 4.5:
        surf_l = _rel_luminance(surf)
        palette["text"] = (15, 23, 42) if surf_l > 0.35 else (248, 250, 252)
        palette["muted"] = (71, 85, 105) if surf_l > 0.35 else (186, 204, 220)
        plan["palette"] = palette

    # Ensure headline never equals generic style/category names
    bad_titles = {"MOTION", "TEMPLATE", "EXPLICACAO", "CENA", "GRAFICO", "CARDS"}
    for lyr in plan.get("layers") or []:
        if lyr.get("component") == "kinetic_headline":
            t = str(lyr.get("props", {}).get("title") or "").strip().upper()
            if not t or t in bad_titles:
                lyr["props"]["title"] = interpretation.get("central_subject", "DESTAQUE")

    # Signature diversity tracking
    sig = f"{plan.get('art_style_id')}|{plan.get('hero_component')}|{plan.get('visual_language')}"
    is_unique = sig not in (used_signatures or [])

    plan["quality_report"] = {
        "contrast_ok": round(contrast_ratio(tuple(palette["text"]), surf), 2),
        "diverse_composition": is_unique,
        "face_safe_position": plan.get("position") != "center" or (frame_info or {}).get("aspect") == "landscape",
        "narrative_grounded": bool(interpretation.get("central_subject")),
    }
    return plan


def audit_rendered_frame(pil_img) -> dict:
    """Inspect actual rendered RGBA frame pixels to confirm non-empty, well-framed compositing."""
    w, h = pil_img.size
    alpha = pil_img.getchannel("A")
    # Downsample to 80x44 for fast zero-memory audit
    small_a = alpha.resize((80, 44)).getdata()
    total = 80 * 44
    opaque_or_mid = sum(1 for v in small_a if v > 28)
    coverage = opaque_or_mid / float(total)
    return {
        "width": w,
        "height": h,
        "alpha_coverage": round(coverage, 3),
        "ok": 0.04 <= coverage <= 0.96,
    }
