"""
B. Art Direction Engine
Plans authentic Motion Design compositions with:
  - ZERO opaque full-stage white/beige slides pasted over the speaker
  - Explicit composition brief (focal element, gaze flow, spatial footprint, development)
  - Adaptive positioning guided by free frame pockets (shoulder walls, compact lower-third, side splits)
  - Varied lighting, materials, typography, camera paths, and color systems
"""
import textwrap

ART_STYLES = {
    "tactical_hud": {
        "id": "tactical_hud",
        "name": "HUD Tático Noturno",
        "bg": (8, 14, 22),
        "primary": (245, 158, 11),      # Amber radar
        "secondary": (239, 68, 68),     # Target Crimson
        "text": (248, 250, 252),
        "muted": (203, 213, 225),
        "headline_font": "BebasNeue-Regular.ttf",
        "accent_font": "DMSans.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "scrim_brackets",
        "material": "radar_glass",
    },
    "editorial_ink": {
        "id": "editorial_ink",
        "name": "Editorial de Alto Contraste",
        "bg": (10, 14, 20),
        "primary": (244, 63, 94),       # Editorial Crimson Coral
        "secondary": (226, 232, 240),   # Cool Alabaster
        "text": (255, 255, 255),
        "muted": (203, 213, 225),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "hairline_floating",
        "material": "editorial_silk",
    },
    "industrial_blueprint": {
        "id": "industrial_blueprint",
        "name": "Blueprint Técnico",
        "bg": (7, 22, 46),
        "primary": (56, 189, 248),      # Blueprint Cyan
        "secondary": (251, 146, 60),    # Copper Torque
        "text": (240, 249, 255),
        "muted": (186, 230, 253),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "Geist.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "tech_crosshairs",
        "material": "anodized_steel",
    },
    "bioluminescent_lab": {
        "id": "bioluminescent_lab",
        "name": "Ciência Bioluminescente",
        "bg": (4, 18, 24),
        "primary": (45, 212, 191),      # Aqua Teal
        "secondary": (103, 232, 249),   # Ice Energy
        "text": (240, 253, 250),
        "muted": (153, 246, 228),
        "headline_font": "Geist.ttf",
        "accent_font": "AppleGaramond-Italic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "pure_halo",
        "material": "energy_glow",
    },
    "cartographic_atlas": {
        "id": "cartographic_atlas",
        "name": "Atlas Cartográfico Translúcido",
        "bg": (9, 20, 34),
        "primary": (16, 185, 129),      # Route Emerald
        "secondary": (245, 208, 138),   # Map Gold Sand
        "text": (248, 250, 252),
        "muted": (203, 213, 225),
        "headline_font": "CreatoDisplay-Bold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "meridian_halo",
        "material": "atlas_glass",
    },
    "archival_chronicle": {
        "id": "archival_chronicle",
        "name": "Crônica Documental",
        "bg": (18, 13, 10),
        "primary": (245, 158, 11),      # Brass Year Gold
        "secondary": (253, 230, 138),   # Archival Warm Ink
        "text": (255, 251, 235),
        "muted": (253, 230, 138),
        "headline_font": "AppleGaramond-BoldItalic.ttf",
        "accent_font": "CreatoDisplay-ExtraBold.otf",
        "body_font": "DMSans.ttf",
        "surface_mode": "chronicle_rule",
        "material": "brass_plate",
    },
    "luxury_3d_stage": {
        "id": "luxury_3d_stage",
        "name": "Palco 3D Volumétrico",
        "bg": (8, 12, 18),
        "primary": (34, 197, 94),       # Kinetic Emerald
        "secondary": (250, 204, 21),    # Metallic Gold
        "text": (255, 255, 255),
        "muted": (187, 247, 208),
        "headline_font": "BebasNeue-Regular.ttf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "pure_halo",
        "material": "metallic_3d",
    },
    "cyber_neural": {
        "id": "cyber_neural",
        "name": "Arquitetura Neural",
        "bg": (10, 7, 22),
        "primary": (34, 211, 238),      # Neon Cyan
        "secondary": (232, 121, 249),   # Magenta Signal
        "text": (248, 250, 252),
        "muted": (221, 214, 254),
        "headline_font": "Geist.ttf",
        "accent_font": "CreatoDisplay-ExtraBold.otf",
        "body_font": "DMSans.ttf",
        "surface_mode": "circuit_halo",
        "material": "hologram_3d",
    },
    "swiss_electric": {
        "id": "swiss_electric",
        "name": "Cinético Elétrico",
        "bg": (9, 14, 28),
        "primary": (96, 165, 250),      # Electric Azure
        "secondary": (248, 250, 252),
        "text": (255, 255, 255),
        "muted": (191, 219, 254),
        "headline_font": "Coolvetica-Regular.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "swiss_pillar",
        "material": "matte_vector",
    },
    "bento_studio": {
        "id": "bento_studio",
        "name": "Bento Hardware Tátil",
        "bg": (22, 24, 30),
        "primary": (34, 197, 94),       # Tactile Emerald
        "secondary": (249, 115, 22),    # Hardware Amber
        "text": (255, 255, 255),
        "muted": (182, 190, 204),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "bento_studio",
        "material": "tactile_bento",
    },
    "editorial_cutaway": {
        "id": "editorial_cutaway",
        "name": "Cutaway Atmosférico Noturno",
        "bg": (11, 13, 20),
        "primary": (239, 68, 68),       # Cinema Scarlet Light-Leak
        "secondary": (248, 250, 252),
        "text": (255, 255, 255),
        "muted": (203, 213, 225),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "pure_halo",
        "material": "cinema_leak",
    },
    "paper_cutaway": {
        "id": "paper_cutaway",
        "name": "Editorial Papel Studio",
        "bg": (242, 240, 235),
        "primary": (244, 63, 94),       # Vivid Rose Ribbon
        "secondary": (17, 24, 39),
        "text": (18, 20, 26),
        "muted": (78, 84, 96),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "surface_mode": "paper_cutaway",
        "material": "editorial_paper",
    },
}

_INTENT_ROUTING = {
    "money_growth": ("motion_3d", "editorial", "luxury_3d_stage", "dolly_in", "wide_scrim"),
    "security_tactical": ("geographic", "narrative_doc", "tactical_hud", "rack_focus", "split_asymmetric"),
    "ai_architecture": ("technological", "motion_3d", "cyber_neural", "orbit_3d", "split_asymmetric"),
    "geo_journey": ("geographic", "narrative_doc", "cartographic_atlas", "pan_sweep", "wide_scrim"),
    "value_comparison": ("editorial", "kinetic_type", "editorial_ink", "tilt_reveal", "dual_wings"),
    "machine_mechanics": ("process_flow", "motion_3d", "industrial_blueprint", "dolly_in", "split_asymmetric"),
    "business_scale": ("motion_3d", "editorial", "bento_studio", "zoom_pan_reveal", "bento_cutaway"),
    "historical_chronology": ("narrative_doc", "editorial", "editorial_cutaway", "dolly_in", "roulette_cutaway"),
    "scientific_principle": ("scientific_edu", "motion_3d", "bioluminescent_lab", "orbit_3d", "split_asymmetric"),
    "process_transformation": ("process_flow", "illustrative", "industrial_blueprint", "pan_sweep", "wide_scrim"),
    "educational_craft": ("illustrative", "kinetic_type", "editorial_ink", "tilt_reveal", "split_asymmetric"),
    "conceptual_focus": ("kinetic_type", "editorial", "editorial_cutaway", "dolly_in", "spotlight_dof"),
}

_DIVERSITY_ROTATION = [
    "bento_studio",
    "editorial_cutaway",
    "paper_cutaway",
    "editorial_ink",
    "bioluminescent_lab",
    "cartographic_atlas",
    "swiss_electric",
    "tactical_hud",
    "cyber_neural",
    "archival_chronicle",
    "industrial_blueprint",
    "luxury_3d_stage",
]


def _pick_spatial_slot(frame_info: dict, intent: str, comp_pattern: str = "", forced_position: str = None, allow_cutaway: bool = True) -> tuple:
    """Place composition using actual analyzed video pockets or cinema cutaways when appropriate."""
    if forced_position in ("fullscreen", "top-center", "top-left", "top-right", "bottom-card", "center"):
        fp = "full" if forced_position == "fullscreen" else ("compact" if forced_position in ("top-left", "top-right") else "wide")
        return forced_position, fp

    if allow_cutaway and comp_pattern in ("bento_cutaway", "roulette_cutaway", "ribbons_cutaway", "spotlight_dof"):
        return "fullscreen", "full"

    aspect = (frame_info or {}).get("aspect", "portrait")
    pockets = (frame_info or {}).get("free_pockets", ["bottom_compact"])
    best = pockets[0] if pockets else "bottom_compact"

    if intent in ("conceptual_focus",) and best in ("top_left_wall", "top_right_wall"):
        return ("top-left" if best == "top_left_wall" else "top-right"), "compact"

    if aspect == "landscape":
        if "right_shoulder" in pockets:
            return "top-right", "compact"
        if "left_shoulder" in pockets:
            return "top-left", "compact"

    return "bottom-card", "wide"


def direct_art(interpretation: dict, frame_info: dict = None, used_styles: list = None, forced_style_id: str = None, forced_position: str = None, custom_accent_hex: str = None, allow_cutaway: bool = True) -> dict:
    """Design a complete visual identity + layout + camera + narrative gaze plan."""
    intent = interpretation.get("narrative_intent", "conceptual_focus")
    lang_main, lang_sec, default_style, cam_motion, comp_pattern = _INTENT_ROUTING.get(
        intent, ("kinetic_type", "editorial", "editorial_ink", "dolly_in", "compact_callout")
    )

    # Alternate cutaways cleanly so presenter remains visible in most segments
    if not allow_cutaway and comp_pattern in ("bento_cutaway", "roulette_cutaway", "ribbons_cutaway", "spotlight_dof"):
        if default_style == "bento_studio":
            default_style = "swiss_electric"
        elif default_style in ("editorial_cutaway", "paper_cutaway"):
            default_style = "editorial_ink"
        comp_pattern = "split_asymmetric" if intent == "business_scale" else "compact_callout"
        if cam_motion == "zoom_pan_reveal":
            cam_motion = "orbit_3d"

    # Multi-item conceptual beats shine with slanted stacked ribbons when cutaway is allowed
    entities = interpretation.get("concrete_entities") or []
    concepts = interpretation.get("abstract_concepts") or []
    if allow_cutaway and intent in ("conceptual_focus", "value_comparison") and (len(concepts) + len(entities) >= 3) and comp_pattern != "ribbons_cutaway":
        comp_pattern = "ribbons_cutaway"
        default_style = "paper_cutaway" if "paper_cutaway" not in (used_styles or []) else "editorial_cutaway"

    style_id = forced_style_id if forced_style_id in ART_STYLES else default_style
    used = list(used_styles or [])
    if not forced_style_id and style_id in used:
        for alt in _DIVERSITY_ROTATION:
            if alt not in used and not (not allow_cutaway and alt in ("bento_studio", "paper_cutaway")):
                style_id = alt
                break

    style = dict(ART_STYLES[style_id])
    if custom_accent_hex and isinstance(custom_accent_hex, str) and custom_accent_hex.startswith("#") and len(custom_accent_hex) == 7:
        hx = custom_accent_hex.lstrip("#")
        style["primary"] = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))

    position, footprint = _pick_spatial_slot(
        frame_info, intent, comp_pattern=comp_pattern, forced_position=forced_position, allow_cutaway=allow_cutaway
    )
    subj = interpretation.get("central_subject", "Conceito")
    metaphor = interpretation.get("visual_metaphor", "")

    composition_brief = {
        "focal_element": metaphor,
        "gaze_flow": f"Elemento visual ({lang_main}) -> manchete '{subj}' -> síntese contextual",
        "footprint": footprint,
        "composition_pattern": comp_pattern,
        "avoids_face": position != "center",
    }

    desc = (
        f"[{style['name']}] {metaphor} "
        f"Composição '{comp_pattern}' ({footprint}) em '{position}', movimento '{cam_motion}'."
    )

    return {
        "visual_language": lang_main,
        "secondary_language": lang_sec,
        "art_style_id": style_id,
        "art_style_name": style["name"],
        "palette": {
            "bg": style["bg"],
            "primary": style["primary"],
            "secondary": style["secondary"],
            "text": style["text"],
            "muted": style["muted"],
            "primary_hex": "#%02X%02X%02X" % style["primary"],
        },
        "typography": {
            "headline_font": style["headline_font"],
            "accent_font": style["accent_font"],
            "body_font": style["body_font"],
        },
        "surface_mode": style["surface_mode"],
        "material": style["material"],
        "layout_mode": comp_pattern,
        "footprint": footprint,
        "position": position,
        "camera": {
            "motion": cam_motion,
            "dolly_scale": 0.08 if cam_motion in ("dolly_in", "orbit_3d", "zoom_pan_reveal") else 0.03,
            "pan_px": 24 if cam_motion in ("pan_sweep", "zoom_pan_reveal") else 10,
        },
        "composition_brief": composition_brief,
        "description": textwrap.shorten(desc, width=210, placeholder="…"),
    }
