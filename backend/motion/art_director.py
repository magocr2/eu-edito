"""
B. Art Direction Engine
Selects bespoke visual language, artistic identity, color system, typography pairing,
spatial integration (guided by frame analysis), depth plan, and camera choreography.
Enforces visual diversity across scenes and prevents generic black/gold/rounded-box repetition.
"""
import textwrap

ART_STYLES = {
    "tactical_hud": {
        "id": "tactical_hud",
        "name": "HUD Tático Operacional",
        "bg": (10, 18, 29),
        "surface": (14, 24, 38),
        "surface_alpha": 212,
        "primary": (245, 158, 11),      # Amber tactical
        "secondary": (239, 68, 68),     # Alert Crimson
        "text": (241, 245, 249),
        "muted": (148, 163, 184),
        "headline_font": "BebasNeue-Regular.ttf",
        "accent_font": "DMSans.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "brackets",
        "material": "matte_hud",
    },
    "editorial_broadsheet": {
        "id": "editorial_broadsheet",
        "name": "Editorial de Revista",
        "bg": (247, 243, 234),
        "surface": (252, 249, 242),
        "surface_alpha": 238,
        "primary": (220, 38, 38),       # Crimson Editorial
        "secondary": (15, 23, 42),      # Carbon Ink
        "text": (17, 24, 39),
        "muted": (75, 85, 99),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "hairline_rule",
        "material": "paper",
    },
    "industrial_blueprint": {
        "id": "industrial_blueprint",
        "name": "Blueprint Técnico / Engenharia",
        "bg": (9, 29, 58),
        "surface": (12, 38, 74),
        "surface_alpha": 218,
        "primary": (56, 189, 248),      # Blueprint Cyan
        "secondary": (251, 146, 60),    # Engineering Copper
        "text": (240, 249, 255),
        "muted": (147, 197, 253),
        "headline_font": "CreatoDisplay-ExtraBold.otf",
        "accent_font": "Geist.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "crosshair_grid",
        "material": "steel",
    },
    "bioluminescent_lab": {
        "id": "bioluminescent_lab",
        "name": "Laboratório Científico",
        "bg": (5, 20, 28),
        "surface": (9, 31, 42),
        "surface_alpha": 204,
        "primary": (20, 184, 166),      # Teal
        "secondary": (103, 232, 249),   # Cyan glow
        "text": (236, 254, 255),
        "muted": (153, 246, 228),
        "headline_font": "Geist.ttf",
        "accent_font": "AppleGaramond-Italic.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "frameless_halo",
        "material": "glass",
    },
    "cartographic_atlas": {
        "id": "cartographic_atlas",
        "name": "Atlas Cartográfico",
        "bg": (12, 26, 43),
        "surface": (17, 36, 58),
        "surface_alpha": 215,
        "primary": (16, 185, 129),      # Emerald Route
        "secondary": (231, 216, 185),   # Atlas Sand
        "text": (248, 250, 252),
        "muted": (186, 210, 228),
        "headline_font": "CreatoDisplay-Bold.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "meridian_frame",
        "material": "atlas",
    },
    "archival_chronicle": {
        "id": "archival_chronicle",
        "name": "Crônica Documental",
        "bg": (26, 20, 15),
        "surface": (244, 232, 209),     # Aged Parchment
        "surface_alpha": 236,
        "primary": (180, 83, 9),        # Burnished Amber
        "secondary": (127, 29, 29),     # Archival Wax Red
        "text": (30, 22, 14),
        "muted": (92, 74, 56),
        "headline_font": "AppleGaramond-BoldItalic.ttf",
        "accent_font": "CreatoDisplay-ExtraBold.otf",
        "body_font": "DMSans.ttf",
        "border_style": "editorial_ticks",
        "material": "parchment",
    },
    "luxury_3d_stage": {
        "id": "luxury_3d_stage",
        "name": "Palco 3D Volumétrico",
        "bg": (11, 15, 23),
        "surface": (18, 24, 36),
        "surface_alpha": 195,
        "primary": (34, 197, 94),       # Kinetic Emerald
        "secondary": (250, 204, 21),    # Specular Gold
        "text": (248, 250, 252),
        "muted": (167, 201, 184),
        "headline_font": "BebasNeue-Regular.ttf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "frameless_halo",
        "material": "metallic_3d",
    },
    "cyber_neural": {
        "id": "cyber_neural",
        "name": "Arquitetura Neural",
        "bg": (13, 9, 26),
        "surface": (21, 16, 42),
        "surface_alpha": 208,
        "primary": (34, 211, 238),      # Neon Cyan
        "secondary": (232, 121, 249),   # Neural Magenta
        "text": (248, 250, 252),
        "muted": (196, 181, 253),
        "headline_font": "Geist.ttf",
        "accent_font": "CreatoDisplay-ExtraBold.otf",
        "body_font": "DMSans.ttf",
        "border_style": "circuit_nodes",
        "material": "hologram",
    },
    "swiss_minimal": {
        "id": "swiss_minimal",
        "name": "Suíço Minimalista",
        "bg": (248, 250, 252),
        "surface": (255, 255, 255),
        "surface_alpha": 236,
        "primary": (37, 99, 235),       # Klein Blue
        "secondary": (15, 23, 42),
        "text": (15, 23, 42),
        "muted": (71, 85, 105),
        "headline_font": "Coolvetica-Regular.otf",
        "accent_font": "AppleGaramond-BoldItalic.ttf",
        "body_font": "DMSans.ttf",
        "border_style": "swiss_bar",
        "material": "matte_clean",
    },
}

_INTENT_TO_LANGUAGE_STYLE = {
    "money_growth": ("motion_3d", "editorial", "luxury_3d_stage", "dolly_in"),
    "security_tactical": ("geographic", "narrative_doc", "tactical_hud", "rack_focus"),
    "ai_architecture": ("technological", "motion_3d", "cyber_neural", "orbit_3d"),
    "geo_journey": ("geographic", "narrative_doc", "cartographic_atlas", "pan_sweep"),
    "value_comparison": ("editorial", "kinetic_type", "editorial_broadsheet", "tilt_reveal"),
    "machine_mechanics": ("process_flow", "motion_3d", "industrial_blueprint", "dolly_in"),
    "business_scale": ("motion_3d", "editorial", "swiss_minimal", "orbit_3d"),
    "historical_chronology": ("narrative_doc", "editorial", "archival_chronicle", "pan_sweep"),
    "scientific_principle": ("scientific_edu", "motion_3d", "bioluminescent_lab", "orbit_3d"),
    "process_transformation": ("process_flow", "illustrative", "industrial_blueprint", "pan_sweep"),
    "educational_craft": ("illustrative", "kinetic_type", "editorial_broadsheet", "tilt_reveal"),
    "conceptual_focus": ("kinetic_type", "illustrative", "swiss_minimal", "dolly_in"),
}

_DIVERSITY_ROTATION = [
    "editorial_broadsheet",
    "bioluminescent_lab",
    "cartographic_atlas",
    "industrial_blueprint",
    "swiss_minimal",
    "cyber_neural",
    "tactical_hud",
    "archival_chronicle",
    "luxury_3d_stage",
]


def _pick_layout(frame_info: dict, intent: str, forced_position: str = None) -> tuple:
    if forced_position in ("top-center", "top-left", "top-right", "bottom-card", "center"):
        slot_map = {
            "top-center": "top_hud",
            "top-left": "asymmetric_left",
            "top-right": "asymmetric_right",
            "bottom-card": "lower_stage",
            "center": "full_plate",
        }
        return forced_position, slot_map[forced_position]

    aspect = (frame_info or {}).get("aspect", "portrait")
    free_slots = (frame_info or {}).get("free_slots", ["lower_stage"])

    if intent in ("security_tactical", "geo_journey", "historical_chronology", "machine_mechanics"):
        # Complex scenes prefer clean lower/side stage without obscuring face
        pos = "bottom-card" if aspect == "portrait" else ("top-right" if "right_stage" in free_slots else "top-left")
        return pos, "lower_stage" if pos == "bottom-card" else "side_column"

    pos = "bottom-card"
    if free_slots and free_slots[0] == "top_floating":
        pos = "top-center"
    elif free_slots and free_slots[0] == "right_stage":
        pos = "top-right"
    elif free_slots and free_slots[0] == "left_stage":
        pos = "top-left"
    return pos, free_slots[0] if free_slots else "lower_stage"


def direct_art(interpretation: dict, frame_info: dict = None, used_styles: list = None, forced_style_id: str = None, forced_position: str = None, custom_accent_hex: str = None) -> dict:
    """Produce a bespoke visual art direction plan based on interpretation + frame space."""
    intent = interpretation.get("narrative_intent", "conceptual_focus")
    lang_main, lang_sec, default_style, cam_motion = _INTENT_TO_LANGUAGE_STYLE.get(
        intent, ("kinetic_type", "editorial", "editorial_broadsheet", "dolly_in")
    )

    style_id = forced_style_id if forced_style_id in ART_STYLES else default_style
    used = list(used_styles or [])
    # Enforce art-style diversity across consecutive scenes unless explicitly forced
    if not forced_style_id and style_id in used:
        for alt in _DIVERSITY_ROTATION:
            if alt not in used:
                style_id = alt
                break

    style = dict(ART_STYLES[style_id])
    if custom_accent_hex and isinstance(custom_accent_hex, str) and custom_accent_hex.startswith("#") and len(custom_accent_hex) == 7:
        hx = custom_accent_hex.lstrip("#")
        style["primary"] = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))

    position, layout_mode = _pick_layout(frame_info, intent, forced_position=forced_position)
    # Invert bright paper cards automatically if background is very bright on frame without surface contrast
    density = "rich" if interpretation.get("complexity") == "high" else "balanced"

    # Build bespoke description of THIS planned visual composition (zero generic boilerplate!)
    subj = interpretation.get("central_subject", "Conceito")
    metaphor = interpretation.get("visual_metaphor", "")
    desc = (
        f"Direção '{style['name']}' ({lang_main} + {lang_sec}): {metaphor} "
        f"Composição posicionada em '{position}' respeitando o quadro do vídeo, "
        f"com câmera '{cam_motion}' e revelação progressiva em 3 atos sobre '{subj.lower()}'."
    )
    desc = textwrap.shorten(desc, width=220, placeholder="…")

    return {
        "visual_language": lang_main,
        "secondary_language": lang_sec,
        "art_style_id": style_id,
        "art_style_name": style["name"],
        "palette": {
            "bg": style["bg"],
            "surface": style["surface"],
            "surface_alpha": style["surface_alpha"],
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
        "border_style": style["border_style"],
        "material": style["material"],
        "layout_mode": layout_mode,
        "position": position,
        "density": density,
        "camera": {
            "motion": cam_motion,
            "dolly_scale": 0.08 if cam_motion in ("dolly_in", "orbit_3d") else 0.03,
            "pan_px": 28 if cam_motion == "pan_sweep" else 10,
            "parallax": 1.0,
        },
        "description": desc,
    }
