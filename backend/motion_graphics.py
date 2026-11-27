"""
Eu Edito — Intelligent Narrative Motion Graphics Facade
Connects the existing Flask / Worker / FFmpeg endpoints cleanly to the
four-module Narrative Motion Design Engine (`backend/motion/`):
  1. Visual Interpreter
  2. Art Direction Engine
  3. Scene Composer + Modular Visual Assets Library
  4. Animation Engine + Visual Quality Gate
"""
from pathlib import Path

from motion.animation_engine import render_scene_clip, render_scene_frame
from motion.art_director import ART_STYLES, direct_art
from motion.frame_analyzer import analyze_video_frames
from motion.interpreter import interpret_segment
from motion.quality_gate import audit_rendered_frame, validate_and_refine_plan
from motion.scene_composer import COMPONENT_REGISTRY, compose_scene_plan

MOTION_CATEGORIES = [
    {"id": "motion_3d", "name": "Motion 3D & Volumétrico"},
    {"id": "editorial", "name": "Motion Editorial & Dados"},
    {"id": "geographic", "name": "Motion Geográfico & Tático"},
    {"id": "technological", "name": "Motion Tecnológico & IA"},
    {"id": "scientific_edu", "name": "Científico & Mecânico"},
    {"id": "narrative_doc", "name": "Narrativo & Documental"},
    {"id": "process_flow", "name": "Processos & Transformação"},
    {"id": "kinetic_type", "name": "Tipografia Cinética & Ilustrativo"},
]

# Configurable visual styles / building blocks exposed cleanly to the existing manual selector
MOTION_TEMPLATES = {
    "auto_narrative": {
        "id": "auto_narrative",
        "category": "editorial",
        "name": "Direção Automática por Roteiro",
        "description": "Interpreta o prompt e escolhe linguagem visual, paleta e composição exclusivas.",
        "default_params": {"title": "Ideia Central", "accent_text": "do roteiro", "visual_prompt": "", "position": "bottom-card", "scale": 100},
    },
    "3d_coins_growth": {
        "id": "3d_coins_growth",
        "category": "motion_3d",
        "name": "3D Financeiro & Meta",
        "description": "Pilhas de moedas 3D com iluminação especular e linha de meta financeira.",
        "default_params": {"title": "Faturamento", "accent_text": "acima da meta", "labels": ["Base", "Evolução", "Meta"], "values": [30, 65, 100], "position": "bottom-card", "scale": 100},
    },
    "3d_pillars_scale": {
        "id": "3d_pillars_scale",
        "category": "motion_3d",
        "name": "Monolitos 3D & Escala",
        "description": "Barras volumétricas em perspectiva 3D para expansão e crescimento.",
        "default_params": {"title": "Crescimento Real", "accent_text": "em escala", "labels": ["F1", "F2", "F3", "Atual"], "values": [25, 50, 75, 100], "position": "bottom-card", "scale": 100},
    },
    "tactical_radar": {
        "id": "tactical_radar",
        "category": "geographic",
        "name": "Radar Tático & Operação",
        "description": "Perímetro operacional com varredura de radar, alvos e unidades convergindo.",
        "default_params": {"title": "Operação em Campo", "accent_text": "em tempo real", "labels": ["Setor N", "Cerco L", "Base S", "Alvo"], "position": "bottom-card", "scale": 100},
    },
    "geo_route_map": {
        "id": "geo_route_map",
        "category": "geographic",
        "name": "Atlas & Rotas Geográficas",
        "description": "Mapa cartográfico com meridianos, relevo e arcos entre cidades.",
        "default_params": {"title": "Trajeto no Mapa", "accent_text": "entre cidades", "labels": ["Origem", "Escala", "Destino"], "position": "bottom-card", "scale": 100},
    },
    "ai_neural_architecture": {
        "id": "ai_neural_architecture",
        "category": "technological",
        "name": "Núcleo 3D & Arquitetura IA",
        "description": "Octaedro 3D giratório conectado a trilhas de circuito e sinais de dados.",
        "default_params": {"title": "Inteligência Artificial", "accent_text": "em arquitetura", "labels": ["Dados", "Rede", "Saída"], "position": "bottom-card", "scale": 100},
    },
    "machine_cutaway": {
        "id": "machine_cutaway",
        "category": "scientific_edu",
        "name": "Mecânica & Engrenagens",
        "description": "Corte técnico em blueprint com engrenagens sincronizadas e pistão.",
        "default_params": {"title": "Mecanismo Interno", "accent_text": "em movimento", "labels": ["Torque", "Eixo", "Pressão"], "position": "bottom-card", "scale": 100},
    },
    "science_orbital": {
        "id": "science_orbital",
        "category": "scientific_edu",
        "name": "Modelo Científico & Ondas",
        "description": "Órbitas atômicas tridimensionais inclinadas + espectro de onda ao vivo.",
        "default_params": {"title": "Princípio Científico", "accent_text": "na física", "labels": ["Núcleo", "Órbita", "Energia"], "position": "bottom-card", "scale": 100},
    },
    "chronology_archive": {
        "id": "chronology_archive",
        "category": "narrative_doc",
        "name": "Crônica & Linha Histórica",
        "description": "Arquivo documental com régua temporal e marcos históricos.",
        "default_params": {"title": "Linha Histórica", "accent_text": "dos fatos", "labels": ["Início", "Virada", "Legado"], "position": "bottom-card", "scale": 100},
    },
    "editorial_comparison": {
        "id": "editorial_comparison",
        "category": "editorial",
        "name": "Comparativo Editorial",
        "description": "Diagramação tipo revista contrastando valores e escalas proporcionais.",
        "default_params": {"title": "Comparação Direta", "accent_text": "em números", "labels": ["Antes", "Depois"], "values": [28, 92], "position": "bottom-card", "scale": 100},
    },
    "process_transformation": {
        "id": "process_transformation",
        "category": "process_flow",
        "name": "Transformação de Estado",
        "description": "Metamorfose visual conectando estado inicial, catalisador e resultado.",
        "default_params": {"title": "Transformação", "accent_text": "do processo", "labels": ["Início", "Catalisador", "Resultado"], "position": "bottom-card", "scale": 100},
    },
    "calligraphy_sheet": {
        "id": "calligraphy_sheet",
        "category": "kinetic_type",
        "name": "Ilustração & Traço Vivo",
        "description": "Folha ilustrativa com traço animado desenhado em tempo real.",
        "default_params": {"title": "Material Prático", "accent_text": "para aplicar", "labels": ["Treino", "Prática"], "position": "bottom-card", "scale": 100},
    },
    "kinetic_headline": {
        "id": "kinetic_headline",
        "category": "kinetic_type",
        "name": "Tipografia Cinética Pura",
        "description": "Composição tipográfica mista sem ruído gráfico desnecessário.",
        "default_params": {"title": "Conceito Central", "accent_text": "em destaque", "position": "bottom-card", "scale": 100},
    },
}

_LEGACY_HERO_ALIAS = {
    "revenue_growth": "3d_pillars_scale",
    "money_flow": "3d_coins_growth",
    "bar_chart": "3d_pillars_scale",
    "donut_share": "editorial_comparison",
    "multi_city_map": "geo_route_map",
    "route_path": "geo_route_map",
    "ai_network": "ai_neural_architecture",
    "data_dashboard": "ai_neural_architecture",
    "timeline_steps": "chronology_archive",
    "concept_callout": "kinetic_headline",
    "vs_split_card": "editorial_comparison",
    "before_after_meter": "editorial_comparison",
    "flow_diagram": "process_transformation",
    "cycle_loop": "science_orbital",
    "counter_kpi": "3d_pillars_scale",
    "badge_alert": "tactical_radar",
    "sketch_calligraphy": "calligraphy_sheet",
    "kinetic_timer": "process_transformation",
    "rocket_boost": "3d_pillars_scale",
    "checklist_reveal": "chronology_archive",
}


def list_catalog():
    return {
        "categories": MOTION_CATEGORIES,
        "templates": list(MOTION_TEMPLATES.values()),
        "art_styles": [{"id": k, "name": v["name"]} for k, v in ART_STYLES.items()],
    }


def _plan_to_ui_params(scene_plan: dict, interpretation: dict, prompt_txt: str) -> dict:
    """Sync declarative `scene_plan` fields cleanly into the UI editable `params` dictionary."""
    hero_lyr = next((l for l in scene_plan.get("layers", []) if l.get("component") != "kinetic_headline"), None)
    head_lyr = next((l for l in scene_plan.get("layers", []) if l.get("component") == "kinetic_headline"), None)
    h_props = (head_lyr or {}).get("props") or {}
    m_props = (hero_lyr or {}).get("props") or {}
    return {
        "title": h_props.get("title") or interpretation.get("central_subject", ""),
        "accent_text": h_props.get("accent") or interpretation.get("accent_phrase", ""),
        "subtitle": h_props.get("subtitle") or interpretation.get("summary_line", ""),
        "metric": (m_props.get("numbers") or [""])[0],
        "labels": m_props.get("labels") or interpretation.get("concrete_entities") or [],
        "values": m_props.get("values") or [30, 68, 96],
        "points": interpretation.get("abstract_concepts") or [],
        "accent_color": scene_plan["palette"]["primary_hex"],
        "position": scene_plan.get("position", "bottom-card"),
        "scale": 100,
        "visual_prompt": prompt_txt,
        "scene_plan": scene_plan,
    }


def build_motion_from_prompt(prompt_text: str, preferred_template_id: str = None, frame_info: dict = None, used_styles: list = None, used_signatures: list = None, duration: float = 3.2) -> dict:
    """Run Visual Interpreter -> Art Director -> Scene Composer -> Quality Gate for a prompt or spoken segment."""
    forced_hero = None
    if preferred_template_id and preferred_template_id != "auto_narrative":
        forced_hero = COMPONENT_REGISTRY.get(preferred_template_id) and preferred_template_id or _LEGACY_HERO_ALIAS.get(preferred_template_id)

    interp = interpret_segment(prompt_text, frame_info=frame_info)
    art = direct_art(interp, frame_info=frame_info, used_styles=used_styles)
    plan = compose_scene_plan(interp, art, duration=duration, forced_hero=forced_hero)
    plan = validate_and_refine_plan(plan, interp, frame_info=frame_info, used_signatures=used_signatures)

    hero_comp = plan["hero_component"]
    tpl_meta = MOTION_TEMPLATES.get(hero_comp, MOTION_TEMPLATES["auto_narrative"])
    return {
        "template_id": hero_comp,
        "template_name": tpl_meta["name"],
        "category": plan["visual_language"],
        "description": plan["description"],
        "scene_plan": plan,
        "params": _plan_to_ui_params(plan, interp, prompt_text),
    }


def analyze_video_for_motion(captions, video_path=None):
    """
    Interpret spoken transcript windows with surrounding context + video frame spatial analysis,
    generating diverse, custom-directed narrative Motion Graphics that replace captions when shown.
    """
    if not captions:
        return []

    # Group captions into coherent thought segments
    windows = []
    i = 0
    while i < len(captions):
        c1 = captions[i]
        text = c1.get("text", "").strip()
        s = float(c1["s"] if c1.get("s") is not None else c1.get("start", 0.0))
        e = float(c1["e"] if c1.get("e") is not None else c1.get("end", s + 2.0))
        while i + 1 < len(captions):
            c_next = captions[i + 1]
            ns = float(c_next["s"] if c_next.get("s") is not None else c_next.get("start", 0.0))
            ne = float(c_next["e"] if c_next.get("e") is not None else c_next.get("end", e))
            if (ns - e) <= 0.65 and (ne - s) <= 6.2 and not text.endswith((".", "!", "?")):
                i += 1
                text = f"{text} {c_next.get('text', '').strip()}".strip()
                e = ne
            else:
                break
        windows.append({"s": s, "e": max(s + 2.2, e), "text": text})
        i += 1

    # Analyze original video frame spatial zones (face, gestures, quiet space, luma)
    sample_ts = [w["s"] + 0.5 for w in windows[:: max(1, len(windows) // 3)]]
    frame_info = analyze_video_frames(video_path, timestamps=sample_ts)

    suggestions = []
    used_styles = []
    used_signatures = []
    last_end = -5.0

    for idx, w in enumerate(windows):
        if suggestions and (w["s"] - last_end < 1.8):
            continue
        prev_txt = windows[idx - 1]["text"] if idx > 0 else ""
        next_txt = windows[idx + 1]["text"] if idx + 1 < len(windows) else ""

        interp = interpret_segment(w["text"], prev_text=prev_txt, next_text=next_txt, frame_info=frame_info)
        if not interp.get("should_render", True):
            continue

        dur = round(min(5.8, max(2.4, w["e"] - w["s"])), 2)
        art = direct_art(interp, frame_info=frame_info, used_styles=used_styles)
        plan = compose_scene_plan(interp, art, duration=dur)
        plan = validate_and_refine_plan(plan, interp, frame_info=frame_info, used_signatures=used_signatures)

        used_styles.append(plan["art_style_id"])
        used_signatures.append(f"{plan['art_style_id']}|{plan['hero_component']}|{plan['visual_language']}")

        hero_comp = plan["hero_component"]
        tpl_meta = MOTION_TEMPLATES.get(hero_comp, MOTION_TEMPLATES["auto_narrative"])
        ui_params = _plan_to_ui_params(plan, interp, w["text"])

        suggestions.append({
            "id": f"mg_{len(suggestions)+1}_{hero_comp}",
            "start": round(w["s"], 2),
            "end": round(w["s"] + dur, 2),
            "excerpt": w["text"],
            "subject": ui_params["title"],
            "category": plan["visual_language"],
            "template_id": hero_comp,
            "template_name": f"{tpl_meta['name']} ({plan['art_style_name']})",
            "reason": plan["description"],
            "relevance": "Alta" if interp.get("complexity") == "high" or interp.get("extracted_numbers") else "Média",
            "position": plan["position"],
            "replace_captions": True,
            "prompt": w["text"],
            "scene_plan": plan,
            "params": ui_params,
            "status": "suggested",
        })
        last_end = w["s"] + dur
        if len(suggestions) >= 4:
            break

    return suggestions


def _apply_user_edits_to_plan(plan: dict, params: dict) -> dict:
    """Sync manual UI edits (title, accent_text, subtitle, accent_color, labels, position) back into `scene_plan`."""
    p = dict(plan)
    if params.get("position"):
        p["position"] = params["position"]
    if isinstance(params.get("accent_color"), str) and params["accent_color"].startswith("#") and len(params["accent_color"]) == 7:
        hx = params["accent_color"].lstrip("#")
        p["palette"] = dict(p.get("palette") or {})
        p["palette"]["primary"] = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        p["palette"]["primary_hex"] = params["accent_color"]
    for lyr in p.get("layers") or []:
        if lyr.get("component") == "kinetic_headline":
            if params.get("title"):
                lyr["props"]["title"] = str(params["title"])
            if "accent_text" in params:
                lyr["props"]["accent"] = str(params["accent_text"] or "")
            if params.get("subtitle"):
                lyr["props"]["subtitle"] = str(params["subtitle"])
        else:
            if isinstance(params.get("labels"), list) and params["labels"]:
                lyr["props"]["labels"] = params["labels"]
            if isinstance(params.get("values"), list) and params["values"]:
                lyr["props"]["values"] = params["values"]
            if params.get("metric"):
                lyr["props"]["numbers"] = [str(params["metric"])]
                lyr["props"]["threshold_label"] = f"META: {str(params['metric']).upper()}"
    return p


def render_motion_clip(
    template_id: str,
    params: dict,
    out_path: Path,
    duration: float = 3.2,
    width: int = 860,
    height: int = 440,
    fps: int = 24,
    on_progress=None,
    cancel_event=None,
) -> Path:
    """Render parameterized or AI-directed `scene_plan` into a lossless RGBA .mov clip."""
    p_dict = dict(params or {})
    plan = p_dict.get("scene_plan")
    if not isinstance(plan, dict) or not plan.get("layers"):
        prompt_seed = str(p_dict.get("visual_prompt") or p_dict.get("subtitle") or p_dict.get("title") or "Cena explicativa")
        built = build_motion_from_prompt(prompt_seed, preferred_template_id=template_id, duration=duration)
        plan = built["scene_plan"]
    plan = _apply_user_edits_to_plan(plan, p_dict)

    # Post-render quality audit check on mid-frame before streaming full clip
    mid_frame = render_scene_frame(plan, 0.55, float(duration) * 0.55, width=width, height=height)
    audit = audit_rendered_frame(mid_frame)
    if not audit["ok"]:
        plan["border_style"] = "hairline_rule"

    return render_scene_clip(
        plan,
        out_path=out_path,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        on_progress=on_progress,
        cancel_event=cancel_event,
    )
