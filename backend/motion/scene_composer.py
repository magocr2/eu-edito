"""
C. Scene Composer
Transforms Visual Interpretation + Art Direction Plan into a validated,
layered declarative `scene_plan` with parallax depth zones, camera keyframes,
narrative beats, and ordered procedural components.
"""
import textwrap

from .assets_library import (
    comp_3d_coins_growth,
    comp_3d_pillars_scale,
    comp_ai_neural_architecture,
    comp_calligraphy_sheet,
    comp_chronology_archive,
    comp_editorial_comparison,
    comp_geo_route_map,
    comp_kinetic_headline,
    comp_machine_cutaway,
    comp_process_transformation,
    comp_science_orbital,
    comp_tactical_radar,
)

COMPONENT_REGISTRY = {
    "3d_coins_growth": comp_3d_coins_growth,
    "3d_pillars_scale": comp_3d_pillars_scale,
    "tactical_radar": comp_tactical_radar,
    "geo_route_map": comp_geo_route_map,
    "machine_cutaway": comp_machine_cutaway,
    "science_orbital": comp_science_orbital,
    "ai_neural_architecture": comp_ai_neural_architecture,
    "chronology_archive": comp_chronology_archive,
    "editorial_comparison": comp_editorial_comparison,
    "process_transformation": comp_process_transformation,
    "calligraphy_sheet": comp_calligraphy_sheet,
    "kinetic_headline": comp_kinetic_headline,
}

_INTENT_HERO_MAP = {
    "money_growth": "3d_coins_growth",
    "security_tactical": "tactical_radar",
    "ai_architecture": "ai_neural_architecture",
    "geo_journey": "geo_route_map",
    "value_comparison": "editorial_comparison",
    "machine_mechanics": "machine_cutaway",
    "business_scale": "3d_pillars_scale",
    "historical_chronology": "chronology_archive",
    "scientific_principle": "science_orbital",
    "process_transformation": "process_transformation",
    "educational_craft": "calligraphy_sheet",
    "conceptual_focus": "process_transformation",
}


def compose_scene_plan(interpretation: dict, art_direction: dict, duration: float = 3.2, forced_hero: str = None) -> dict:
    """Build a complete declarative, schema-validated `scene_plan` ready for preview & export."""
    intent = interpretation.get("narrative_intent", "conceptual_focus")
    hero_kind = forced_hero if forced_hero in COMPONENT_REGISTRY else _INTENT_HERO_MAP.get(intent, "process_transformation")

    # Special case: calligraphy vs stopwatch vs generic craft
    summary_low = (interpretation.get("summary_line") or "").lower()
    if hero_kind == "calligraphy_sheet" and not any(w in summary_low for w in ("caligraf", "escrev", "letra", "imprim", "caderno", "papel")):
        hero_kind = "process_transformation"

    nums = interpretation.get("extracted_numbers") or []
    places = interpretation.get("places") or []
    entities = interpretation.get("concrete_entities") or []
    concepts = interpretation.get("abstract_concepts") or []
    labels = places if places else (entities if entities else concepts)
    if not labels:
        labels = ["Contexto", "Ação", "Impacto"]

    thresh_lbl = f"META: {nums[0].upper()}" if nums else ""
    headline_props = {
        "title": interpretation.get("central_subject") or "CENÁRIO",
        "accent": interpretation.get("accent_phrase") or "",
        "subtitle": interpretation.get("summary_line") or "",
        "size": 52 if art_direction["art_style_id"] != "tactical_hud" else 58,
    }
    hero_props = {
        "labels": labels[:4],
        "numbers": nums[:4],
        "threshold_label": thresh_lbl,
        "values": _parse_values(nums),
    }

    layers = []
    # Typographic Header Layer (z=1.0 foreground, enters immediately on beat 1)
    if intent == "conceptual_focus" and not nums and len(concepts) <= 1:
        # Pure kinetic editorial typography without decorative graphic clutter
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.06, 0.24, 0.94, 0.78],
            "props": {**headline_props, "size": 66},
        })
    elif hero_kind in ("calligraphy_sheet", "tactical_radar", "machine_cutaway", "science_orbital"):
        # Left/Right split inside the stage: Visual Hero on Left + Editorial Hierarchy on Right (or Top/Bottom)
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.05, 0.06, 0.95, 0.34],
            "props": headline_props,
        })
        layers.append({
            "component": hero_kind,
            "z_depth": 0.65,
            "t_in": 0.08,
            "t_out": 1.0,
            "box": [0.05, 0.35, 0.95, 0.94],
            "props": hero_props,
        })
    else:
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.05, 0.05, 0.95, 0.32],
            "props": headline_props,
        })
        layers.append({
            "component": hero_kind,
            "z_depth": 0.65,
            "t_in": 0.06,
            "t_out": 1.0,
            "box": [0.05, 0.33, 0.95, 0.95],
            "props": hero_props,
        })

    return {
        "version": 4,
        "intent": intent,
        "hero_component": hero_kind,
        "visual_language": art_direction["visual_language"],
        "secondary_language": art_direction["secondary_language"],
        "art_style_id": art_direction["art_style_id"],
        "art_style_name": art_direction["art_style_name"],
        "border_style": art_direction["border_style"],
        "material": art_direction["material"],
        "layout_mode": art_direction["layout_mode"],
        "position": art_direction["position"],
        "palette": art_direction["palette"],
        "typography": art_direction["typography"],
        "camera": art_direction["camera"],
        "duration": round(float(duration), 2),
        "beats": interpretation.get("narrative_beats") or [],
        "description": art_direction["description"],
        "layers": layers,
    }


def _parse_values(nums: list) -> list:
    import re
    out = []
    for n in (nums or [])[:4]:
        d = re.sub(r"[^\d.]", "", str(n).replace(",", "."))
        try:
            v = float(d)
            if v > 0:
                out.append(v)
        except Exception:
            pass
    if len(out) == 1:
        return [round(out[0] * 0.25, 1), round(out[0] * 0.58, 1), out[0]]
    return out if len(out) >= 2 else [28.0, 56.0, 84.0, 100.0]
