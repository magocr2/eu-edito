"""
C. Scene Composer
Builds spatially varied, bespoke Motion Design compositions (`split_asymmetric`,
`dual_wings`, `wide_ribbon`, `wide_scrim`, `compact_callout`) from interpreted intent + art direction.
Never uses a single universal box/card layout across scenes.
"""
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
    "conceptual_focus": "kinetic_headline",
}


def compose_scene_plan(interpretation: dict, art_direction: dict, duration: float = 3.2, forced_hero: str = None) -> dict:
    """Compile Visual Interpretation + Art Direction into a varied spatial composition."""
    intent = interpretation.get("narrative_intent", "conceptual_focus")
    hero_kind = forced_hero if forced_hero in COMPONENT_REGISTRY else _INTENT_HERO_MAP.get(intent, "kinetic_headline")

    nums = interpretation.get("extracted_numbers") or []
    places = interpretation.get("places") or []
    entities = interpretation.get("concrete_entities") or []
    concepts = interpretation.get("abstract_concepts") or []
    labels = places if places else (concepts if concepts else entities)
    if not labels:
        labels = ["Início", "Evolução", "Resultado"]

    thresh_lbl = f"META: {nums[0].upper()}" if nums else ""
    headline_props = {
        "title": interpretation.get("central_subject") or "CENÁRIO",
        "accent": interpretation.get("accent_phrase") or "",
        "subtitle": interpretation.get("concise_tag") or "",
        "size": 52 if art_direction["art_style_id"] != "tactical_hud" else 58,
    }
    hero_props = {
        "labels": labels[:4],
        "numbers": nums[:4],
        "threshold_label": thresh_lbl,
        "values": _parse_values(nums),
    }

    pattern = art_direction.get("layout_mode", "wide_scrim")
    layers = []

    if hero_kind == "kinetic_headline" or pattern == "compact_callout":
        # Pure kinetic editorial typography without decorative graphic bloat
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.06, 0.22, 0.94, 0.78],
            "props": {**headline_props, "size": 64},
        })
    elif pattern == "split_asymmetric" and hero_kind in ("tactical_radar", "3d_pillars_scale", "science_orbital", "calligraphy_sheet"):
        # Left Visual Focus + Right Balanced Editorial Lockup (breaks top-down monotony!)
        layers.append({
            "component": hero_kind,
            "z_depth": 0.75,
            "t_in": 0.04,
            "t_out": 1.0,
            "box": [0.04, 0.14, 0.50, 0.92],
            "props": hero_props,
        })
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.53, 0.26, 0.96, 0.80],
            "props": {**headline_props, "size": 46},
        })
    elif pattern == "dual_wings" or hero_kind == "editorial_comparison":
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.05, 0.06, 0.95, 0.30],
            "props": {**headline_props, "size": 48},
        })
        layers.append({
            "component": "editorial_comparison",
            "z_depth": 0.75,
            "t_in": 0.08,
            "t_out": 1.0,
            "box": [0.05, 0.32, 0.95, 0.92],
            "props": hero_props,
        })
    else:
        layers.append({
            "component": "kinetic_headline",
            "z_depth": 1.0,
            "t_in": 0.0,
            "t_out": 1.0,
            "box": [0.05, 0.05, 0.95, 0.30],
            "props": headline_props,
        })
        layers.append({
            "component": hero_kind,
            "z_depth": 0.65,
            "t_in": 0.06,
            "t_out": 1.0,
            "box": [0.05, 0.32, 0.95, 0.94],
            "props": hero_props,
        })

    return {
        "version": 5,
        "intent": intent,
        "hero_component": hero_kind,
        "visual_language": art_direction["visual_language"],
        "secondary_language": art_direction["secondary_language"],
        "art_style_id": art_direction["art_style_id"],
        "art_style_name": art_direction["art_style_name"],
        "surface_mode": art_direction["surface_mode"],
        "material": art_direction["material"],
        "layout_mode": pattern,
        "footprint": art_direction.get("footprint", "wide"),
        "position": art_direction["position"],
        "palette": art_direction["palette"],
        "typography": art_direction["typography"],
        "camera": art_direction["camera"],
        "composition_brief": art_direction.get("composition_brief") or {},
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
