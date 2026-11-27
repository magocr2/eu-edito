"""
Eu Edito — Intelligent Speech-to-Prompt Motion Graphics Engine
Generates rich, visually distinct, self-explanatory Motion Graphics driven directly by what
is spoken in the video (and/or user-edited visual prompt). Designed to replace captions
during key explanatory segments with multi-stage animated RGBA overlays.
"""
import json
import math
import os
import re
import subprocess
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"

MOTION_CATEGORIES = [
    {"id": "negocios", "name": "Negócios e dinheiro"},
    {"id": "graficos", "name": "Gráficos e estatísticas"},
    {"id": "mapas", "name": "Mapas e localização"},
    {"id": "tecnologia", "name": "Tecnologia e inovação"},
    {"id": "educacao", "name": "Educação e explicações"},
    {"id": "comparacoes", "name": "Comparações"},
    {"id": "processos", "name": "Processos e diagramas"},
    {"id": "elementos", "name": "Elementos visuais diversos"},
]

MOTION_TEMPLATES = {
    "revenue_growth": {
        "id": "revenue_growth",
        "category": "negocios",
        "name": "Crescimento & Curva",
        "description": "Eixo analítico, curva Bézier ascendente com marcos da fala e resumo explicativo.",
        "default_params": {
            "title": "Crescimento Real",
            "subtitle": "Evolução destacada na fala",
            "values": [20, 38, 62, 100],
            "labels": ["Início", "Avanço", "Escala", "Topo"],
            "points": ["Evolução contínua", "Resultado multiplicado"],
            "metric": "+3x",
            "accent_color": "#22C55E",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "money_flow": {
        "id": "money_flow",
        "category": "negocios",
        "name": "Dinheiro & Fluxo Financeiro",
        "description": "Pilhas de moedas 3D douradas e fluxo financeiro conectado a cartão de retorno.",
        "default_params": {
            "title": "Retorno Financeiro",
            "subtitle": "Movimentação de valor",
            "values": [40, 72, 100],
            "labels": ["Investido", "Fluxo", "Retorno"],
            "points": ["Fluxo positivo", "Ganho direto"],
            "metric": "R$",
            "accent_color": "#FACC15",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "bar_chart": {
        "id": "bar_chart",
        "category": "graficos",
        "name": "Gráfico de Barras",
        "description": "Colunas estatísticas escalonadas com valores flutuantes e legenda por coluna.",
        "default_params": {
            "title": "Comparativo em Barras",
            "subtitle": "Dados citados no trecho",
            "values": [28, 52, 76, 98],
            "labels": ["Fase 1", "Fase 2", "Fase 3", "Atual"],
            "points": ["Crescimento progressivo por etapa"],
            "metric": "DADOS",
            "accent_color": "#38BDF8",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "donut_share": {
        "id": "donut_share",
        "category": "graficos",
        "name": "Anel Estatístico / %",
        "description": "Indicador circular luminoso à esquerda com detalhamento dos itens à direita.",
        "default_params": {
            "title": "Proporção & Impacto",
            "subtitle": "Divisão citada",
            "values": [78, 54, 32],
            "labels": ["Principal", "Secundário", "Base"],
            "points": ["Parcela dominante destacada na fala"],
            "metric": "78%",
            "accent_color": "#A855F7",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
        },
    },
    "multi_city_map": {
        "id": "multi_city_map",
        "category": "mapas",
        "name": "Mapa & Localizações",
        "description": "Grade cartográfica com silhuetas de território, pins com radar e rótulos dos locais.",
        "default_params": {
            "title": "Mapa de Atuação",
            "subtitle": "Locais mencionados",
            "values": [3],
            "labels": ["Local 1", "Local 2", "Local 3"],
            "points": ["Conexão entre múltiplas localidades"],
            "metric": "MAPA",
            "accent_color": "#22C55E",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "fade",
        },
    },
    "route_path": {
        "id": "route_path",
        "category": "mapas",
        "name": "Rota & Trajeto",
        "description": "Origem e destino ligados por arco curvo animado com rastreador em movimento.",
        "default_params": {
            "title": "Trajeto Direto",
            "subtitle": "Deslocamento explicado",
            "values": [100],
            "labels": ["Origem", "Destino"],
            "points": ["Percurso completo entre os pontos"],
            "metric": "ROTA",
            "accent_color": "#38BDF8",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "smooth",
            "entry_exit": "slide-up",
        },
    },
    "ai_network": {
        "id": "ai_network",
        "category": "tecnologia",
        "name": "Núcleo Neural & IA",
        "description": "Processador hexagonal giratório com sinapses neurais e pulsos de informação.",
        "default_params": {
            "title": "Motor Inteligente",
            "subtitle": "Processamento contextual",
            "values": [95],
            "labels": ["Entrada", "Núcleo IA", "Resultado"],
            "points": ["Leitura do contexto", "Automação instantânea"],
            "metric": "IA",
            "accent_color": "#38BDF8",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
        },
    },
    "data_dashboard": {
        "id": "data_dashboard",
        "category": "tecnologia",
        "name": "Painel de Sistema",
        "description": "Interface moderna de aplicativo com equalizador, sparkline e cartões de status.",
        "default_params": {
            "title": "Sistema ao Vivo",
            "subtitle": "Métricas em tempo real",
            "values": [38, 64, 52, 84, 96],
            "labels": ["Ativo", "Sincronizado"],
            "points": ["Operação automática sem trabalho manual"],
            "metric": "LIVE",
            "accent_color": "#4ADE80",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "timeline_steps": {
        "id": "timeline_steps",
        "category": "educacao",
        "name": "Linha do Tempo",
        "description": "Trilha cronológica luminosa com marcos numerados e cards explicativos.",
        "default_params": {
            "title": "Linha do Tempo",
            "subtitle": "Sequência dos fatos",
            "values": [1, 2, 3],
            "labels": ["Início", "Virada", "Hoje"],
            "points": ["Evolução clara do começo até o resultado"],
            "metric": "TIMELINE",
            "accent_color": "#F59E0B",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "concept_callout": {
        "id": "concept_callout",
        "category": "educacao",
        "name": "Explicação em Blocos",
        "description": "Destaque editorial com marca-texto animado e lista de pontos explicativos.",
        "default_params": {
            "title": "Entenda na Prática",
            "subtitle": "Síntese da explicação",
            "values": [100],
            "labels": ["Ideia Central"],
            "points": ["Primeiro ponto explicado", "Conclusão prática"],
            "metric": "FOCO",
            "accent_color": "#38BDF8",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "vs_split_card": {
        "id": "vs_split_card",
        "category": "comparacoes",
        "name": "Duelo Antes vs Depois",
        "description": "Painel dividido vermelho vs verde com selo VS central e contrastes reais.",
        "default_params": {
            "title": "Comparação Direta",
            "subtitle": "Dois cenários em contraste",
            "values": [28, 94],
            "labels": ["Antes", "Depois"],
            "points": ["Lento e manual", "Rápido e automático"],
            "metric": "VS",
            "accent_color": "#22C55E",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "before_after_meter": {
        "id": "before_after_meter",
        "category": "comparacoes",
        "name": "Escala de Evolução",
        "description": "Barras horizontais de nível antes/depois com indicador de salto.",
        "default_params": {
            "title": "Salto de Nível",
            "subtitle": "Transformação comparada",
            "values": [24, 92],
            "labels": ["Cenário Anterior", "Novo Padrão"],
            "points": ["Diferença expressiva entre os dois momentos"],
            "metric": "EVOLUÇÃO",
            "accent_color": "#4ADE80",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
        },
    },
    "flow_diagram": {
        "id": "flow_diagram",
        "category": "processos",
        "name": "Fluxograma Passo a Passo",
        "description": "Blocos verticais/horizontais conectados por setas luminosas sequenciais.",
        "default_params": {
            "title": "Como Funciona",
            "subtitle": "Passo a passo na prática",
            "values": [1, 2, 3],
            "labels": ["Passo 1", "Passo 2", "Passo 3"],
            "points": ["Execução organizada em etapas"],
            "metric": "FLUXO",
            "accent_color": "#22C55E",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "cycle_loop": {
        "id": "cycle_loop",
        "category": "processos",
        "name": "Ciclo Contínuo (3 Nós)",
        "description": "Triângulo orbital com arcos curvos e indicador giratório ligando as etapas.",
        "default_params": {
            "title": "Ciclo Contínuo",
            "subtitle": "Engrenagem do processo",
            "values": [3],
            "labels": ["Ação", "Resultado", "Melhoria"],
            "points": ["Processo que se retroalimenta"],
            "metric": "CICLO",
            "accent_color": "#A855F7",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "smooth",
            "entry_exit": "fade",
        },
    },
    "counter_kpi": {
        "id": "counter_kpi",
        "category": "elementos",
        "name": "Contador Cinético",
        "description": "Número gigante em contagem progressiva com raios radiais e faixa de contexto.",
        "default_params": {
            "title": "Número Destaque",
            "subtitle": "Registro citado",
            "values": [100],
            "labels": ["Marco"],
            "points": ["Dado exato mencionado na fala"],
            "metric": "100%",
            "accent_color": "#FACC15",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "badge_alert": {
        "id": "badge_alert",
        "category": "elementos",
        "name": "Fato / Contexto Editorial",
        "description": "Faixa de destaque com radar pulsante e síntese visual de acontecimento.",
        "default_params": {
            "title": "Ponto Importante",
            "subtitle": "Contexto da fala",
            "values": [100],
            "labels": ["Atenção"],
            "points": ["Informação central destacada"],
            "metric": "!",
            "accent_color": "#F43F5E",
            "position": "center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
}


def list_catalog():
    return {"categories": MOTION_CATEGORIES, "templates": list(MOTION_TEMPLATES.values())}


def _hex_to_rgb(hx: str):
    h = (hx or "#22C55E").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (34, 197, 94)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (34, 197, 94)


def _ease(t: float, mode: str = "cubic-out") -> float:
    t = max(0.0, min(1.0, t))
    if mode == "spring":
        if t < 0.72:
            u = t / 0.72
            return 1.06 * (1.0 - (1.0 - u) ** 3)
        u = (t - 0.72) / 0.28
        return 1.06 - 0.06 * (u * u * (3 - 2 * u))
    if mode == "smooth":
        return t * t * (3.0 - 2.0 * t)
    return 1.0 - (1.0 - t) ** 3


def _load_font(filename: str, size: int):
    fp = FONTS_DIR / filename
    try:
        if fp.exists():
            return ImageFont.truetype(str(fp), max(10, int(size)))
    except Exception:
        pass
    return ImageFont.load_default()


def _clean_clauses(text: str, max_items: int = 3, max_chars: int = 26) -> list:
    """Split spoken Portuguese sentence cleanly into meaningful short phrases without chopping words."""
    parts = re.split(r"[,;:.!?]+|\b(?:e depois|depois|então|mas|porém|enquanto|para que|onde|e)\b", text, flags=re.I)
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) < 3:
            continue
        if len(p) > max_chars:
            wrapped = textwrap.wrap(p, width=max_chars, break_long_words=False)
            p = wrapped[0] if wrapped else p[:max_chars]
        out.append(p)
        if len(out) >= max_items:
            break
    if not out and text.strip():
        out = textwrap.wrap(text.strip(), width=max_chars, break_long_words=False)[:max_items]
    return out


def _wrap_lines(text: str, width_chars: int = 34, max_lines: int = 2) -> list:
    return textwrap.wrap(re.sub(r"\s+", " ", (text or "").strip()), width=width_chars, break_long_words=False)[:max_lines]


def _parse_speech_to_scene(text: str, preferred_tid: str = None) -> dict:
    """Turn a spoken phrase or user prompt into structured explanatory Motion scene parameters."""
    txt = re.sub(r"\s+", " ", (text or "").strip())
    low = txt.lower()
    nums = re.findall(r"r\$\s*[\d.,]+(?:\s*(?:mil|mi|bi|m|k))?|\d+(?:[.,]\d+)?\s*%|\b\d+(?:[.,]\d+)?\b", txt, re.I)

    tid = preferred_tid if preferred_tid in MOTION_TEMPLATES else None
    metric = ""
    title = ""
    subtitle = ""
    labels = []
    values = [30, 62, 95]
    points = _clean_clauses(txt, max_items=3, max_chars=34)

    if not tid:
        if re.search(r"triplic|dobr|quadruplic|faturament|receit|lucr|venda|cresc", low):
            tid = "revenue_growth"
        elif re.search(r"r\$|reais|dinheir|invest|lucr|pag|ganh|fatur", low):
            tid = "money_flow"
        elif re.search(r"rota|trajet|viag|caminh|saindo|chegando|indo para", low):
            tid = "route_path"
        elif re.search(r"cidad|estad|pa[ií]s|regi[aã]o|local|mapa|lugares|brasil|norte|sul", low):
            tid = "multi_city_map"
        elif re.search(r"antes.*depois|em vez|enquanto|compar|melhor.*que|pior.*que|versus|diferen", low):
            tid = "vs_split_card"
        elif re.search(r"ciclo|gira|volta|loop|cont[ií]nu", low):
            tid = "cycle_loop"
        elif re.search(r"primeiro|segundo|terceiro|etapa|passo|processo|fluxo|mecanism|funciona", low):
            tid = "flow_diagram"
        elif re.search(r"intelig[eê]ncia|ia\b|algoritm|neural|rede|autom|motor", low):
            tid = "ai_network"
        elif re.search(r"sistema|aplicativo|painel|dados|tela|plataforma|app\b", low):
            tid = "data_dashboard"
        elif re.search(r"\b(19|20)\d{2}\b|linha do tempo|cronolog|hist[oó]ri|anos|meses", low):
            tid = "timeline_steps"
        elif any("%" in n for n in nums):
            tid = "donut_share"
        elif len(nums) >= 2:
            tid = "bar_chart"
        elif nums:
            tid = "counter_kpi"
        elif re.search(r"cuidado|aten[çc]|erro|alerta|nunca|proibid", low):
            tid = "badge_alert"
        else:
            tid = "concept_callout"

    tpl = MOTION_TEMPLATES[tid]
    merged = dict(tpl["default_params"])

    # Extract real multi-word proper nouns / places (e.g., "São Paulo", "Lisboa")
    tail_txt = " ".join(txt.split()[1:]) if len(txt.split()) > 1 else ""
    cap_words = [
        m.strip(".,!?;:")
        for m in re.findall(r"\b[A-ZÀ-Ú][a-zà-ú]{1,}(?:\s+[A-ZÀ-Ú][a-zà-ú]{1,})*", tail_txt)
        if m.lower() not in ("agora", "antes", "depois", "passo", "hoje")
    ]

    if tid in ("revenue_growth", "money_flow", "bar_chart"):
        if "triplic" in low:
            metric = "3X"
            values = [25, 50, 75, 100]
            labels = ["Base", "2x", "Salto", "3X"]
            title = "Crescimento 3x"
        elif "dobr" in low:
            metric = "2X"
            values = [35, 55, 78, 100]
            labels = ["Base", "Avanço", "Dobro"]
            title = "Resultado 2x"
        elif nums:
            metric = nums[0].upper()
            pct_nums = [n for n in nums if "%" in n]
            parsed_v = []
            for n in nums[:4]:
                digits = re.sub(r"[^\d.]", "", n.replace(",", "."))
                try:
                    parsed_v.append(max(5.0, float(digits)))
                except Exception:
                    pass
            if pct_nums and tid == "revenue_growth" and re.search(r"cresc|subi|aument|escal", low):
                try:
                    top_v = float(re.sub(r"[^\d.]", "", pct_nums[0].replace(",", ".")) or 100)
                except Exception:
                    top_v = 100.0
                values = [round(top_v * 0.22, 1), round(top_v * 0.54, 1), round(top_v, 1)]
                labels = ["Início", "Avanço", pct_nums[0][:10]]
            else:
                values = parsed_v if len(parsed_v) >= 3 else ([round(parsed_v[0] * 0.35, 1), round(parsed_v[0] * 0.68, 1), parsed_v[0]] if parsed_v else [30, 62, 95])
                labels = [n[:10] for n in nums[:4]] if len(nums) >= 3 else _clean_clauses(txt, 3, 14)
            title = tpl["name"]
        else:
            metric = "R$" if tid == "money_flow" else "ALTA"
            labels = _clean_clauses(txt, 3, 14) or merged["labels"]
            title = tpl["name"]
    elif tid in ("multi_city_map", "route_path"):
        title = "Trajeto no Mapa" if tid == "route_path" else "Locais no Mapa"
        metric = nums[0].upper() if nums else f"{max(2, len(cap_words))} LOCAIS"
        labels = cap_words[:3] if len(cap_words) >= 2 else (_clean_clauses(txt, 3, 14) or merged["labels"])
    elif tid in ("vs_split_card", "before_after_meter"):
        title = "Comparativo Real"
        metric = "VS"
        vs_parts = [p.strip(" ,.;:!?") for p in re.split(r"\b(?:vs\.?|contra|mas agora|e agora|enquanto)\b", txt, maxsplit=1, flags=re.I) if p.strip(" ,.;:!?")]
        clauses = vs_parts if len(vs_parts) >= 2 else _clean_clauses(txt, 2, 24)
        labels = [clauses[0][:20] if clauses else "Antes", clauses[1][:20] if len(clauses) > 1 else "Depois"]
        points = [c[:32] for c in clauses[:2]]
    elif tid in ("flow_diagram", "cycle_loop", "timeline_steps"):
        title = tpl["name"]
        clauses = _clean_clauses(txt, 3, 20)
        labels = clauses if len(clauses) >= 2 else merged["labels"]
        metric = f"{len(labels)} ETAPAS"
    elif tid in ("donut_share", "counter_kpi"):
        metric = nums[0].upper() if nums else "FOCO"
        title = "Dado Citado"
        labels = _clean_clauses(txt, 3, 16) or [metric]
        if nums:
            d = re.sub(r"[^\d.]", "", nums[0].replace(",", "."))
            try:
                values = [min(100.0, max(10.0, float(d)))]
            except Exception:
                pass
    else:
        title = tpl["name"]
        clauses = _clean_clauses(txt, 3, 22)
        labels = clauses if clauses else merged["labels"]
        metric = nums[0].upper() if nums else merged["metric"]

    # Concise clean subtitle grounded strictly in spoken phrase
    sub_lines = _wrap_lines(txt, width_chars=36, max_lines=1)
    subtitle = sub_lines[0] if sub_lines else tpl["description"]

    merged.update({
        "title": title[:28],
        "subtitle": subtitle[:38],
        "metric": str(metric)[:14],
        "labels": [str(x)[:18] for x in (labels or merged["labels"])[:4]],
        "values": values,
        "points": [str(x)[:36] for x in (points or [subtitle])[:3]],
        "visual_prompt": f"Ilustrar '{tpl['name']}': {txt[:120]}",
    })
    return {"template_id": tid, "template_name": tpl["name"], "category": tpl["category"], "params": merged}


def build_motion_from_prompt(prompt_text: str, preferred_template_id: str = None) -> dict:
    """Build detailed Motion Graphic scene strictly from spoken text or user prompt (Groq LLM + fallback)."""
    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if groq_key:
        try:
            catalog_summary = [{"id": k, "name": v["name"], "category": v["category"]} for k, v in MOTION_TEMPLATES.items()]
            pref_note = f"Use preferencialmente template_id='{preferred_template_id}'." if preferred_template_id in MOTION_TEMPLATES else ""
            sys_prompt = (
                "Converta a fala ou prompt do usuário em uma cena de Motion Graphic explicativa que substitui a legenda.\n"
                "REGRAS: 1) NÃO invente números/datas/cidades fora do texto; 2) Extraia 2 ou 3 rótulos/etapas curtos direto do texto em 'labels' "
                "e 2 frases curtas explicativas em 'points'; 3) Retorne APENAS JSON: "
                "{\"template_id\": string, \"title\": string, \"subtitle\": string, \"metric\": string, \"labels\": [string], "
                "\"values\": [number], \"points\": [string], \"visual_prompt\": string}.\n"
                f"{pref_note}\nTemplates: {json.dumps(catalog_summary, ensure_ascii=False)}\nTexto: {prompt_text}"
            )
            req_body = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": sys_prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=req_body,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                parsed = json.loads(json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"])
            tid = parsed.get("template_id")
            if tid not in MOTION_TEMPLATES:
                tid = preferred_template_id if preferred_template_id in MOTION_TEMPLATES else "concept_callout"
            tpl = MOTION_TEMPLATES[tid]
            merged = dict(tpl["default_params"])
            for k in ("title", "subtitle", "metric", "visual_prompt"):
                if parsed.get(k):
                    merged[k] = str(parsed[k])[:42 if k != "visual_prompt" else 140]
            if isinstance(parsed.get("labels"), list) and parsed["labels"]:
                merged["labels"] = [str(x)[:18] for x in parsed["labels"][:4]]
            if isinstance(parsed.get("points"), list) and parsed["points"]:
                merged["points"] = [str(x)[:36] for x in parsed["points"][:3]]
            if isinstance(parsed.get("values"), list) and parsed["values"]:
                merged["values"] = [float(x) for x in parsed["values"][:5] if isinstance(x, (int, float))] or merged["values"]
            return {"template_id": tid, "template_name": tpl["name"], "category": tpl["category"], "params": merged}
        except Exception:
            pass
    return _parse_speech_to_scene(prompt_text, preferred_tid=preferred_template_id)


def _sample_scene_brightness(video_path: Path, timestamps) -> dict:
    try:
        from processor import find_ffmpeg
        ffmpeg, _ = find_ffmpeg()
    except Exception:
        return {}
    out = {}
    for t in (timestamps or [])[:4]:
        try:
            cmd = [ffmpeg, "-ss", f"{max(0.0, float(t)):.2f}", "-i", str(video_path), "-frames:v", "1", "-vf", "scale=32:56,format=gray", "-f", "rawvideo", "-"]
            r = subprocess.run(cmd, capture_output=True, timeout=6)
            if r.returncode == 0 and len(r.stdout) >= 32 * 56:
                out[round(float(t), 2)] = {"top_luma": round(sum(r.stdout[: 32 * 18]) / float(32 * 18), 1)}
        except Exception:
            pass
    return out


def analyze_video_for_motion(captions, video_path=None):
    """
    Analyze full timestamped transcript into coherent thought windows, generate a bespoke
    visual prompt + explanatory Motion Graphic for high-value moments (substituting captions).
    """
    if not captions:
        return []
    if video_path and Path(video_path).exists():
        _sample_scene_brightness(Path(video_path), [c.get("s", c.get("start", 0.0)) for c in captions[:: max(1, len(captions) // 4)]])

    # Group captions into complete thought windows (2-3 captions or until punctuation)
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
            if (ns - e) <= 0.65 and (ne - s) <= 6.8 and not text.endswith((".", "!", "?")):
                i += 1
                text = f"{text} {c_next.get('text', '').strip()}".strip()
                e = ne
            else:
                break
        windows.append({"s": s, "e": max(s + 2.2, e), "text": text})
        i += 1

    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if groq_key:
        try:
            transcript_lines = [f"[{round(w['s'], 2)}s - {round(w['e'], 2)}s] {w['text']}" for w in windows]
            catalog_summary = [{"id": k, "category": v["category"], "name": v["name"]} for k, v in MOTION_TEMPLATES.items()]
            prompt = (
                "Você é diretor de Motion Graphics. Analise os trechos da fala abaixo e escolha até 4 momentos onde um Motion Graphic "
                "explicativo SUBSTITUI a legenda para ilustrar exatamente o que está sendo dito.\n"
                "REGRAS ESTRITAS:\n"
                "1. Crie um 'visual_prompt' fiel ao que foi falado naquele trecho.\n"
                "2. Extraia 'labels' (2-4 rótulos curtos reais da fala), 'points' (2-3 pontos explicativos reais da fala) e 'metric' (número/termo dito).\n"
                "3. NUNCA invente números, cidades ou fatos não ditos.\n"
                "4. Retorne APENAS JSON: {\"suggestions\": [{\"start\": number, \"end\": number, \"excerpt\": string, "
                "\"subject\": string, \"template_id\": string, \"reason\": string, \"relevance\": \"Alta\"|\"Média\", "
                "\"visual_prompt\": string, \"title\": string, \"subtitle\": string, \"metric\": string, "
                "\"labels\": [string], \"values\": [number], \"points\": [string]}]}.\n\n"
                f"TEMPLATES:\n{json.dumps(catalog_summary, ensure_ascii=False)}\n\n"
                "TRECHOS:\n" + "\n".join(transcript_lines[:40])
            )
            req_body = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=req_body,
                headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                parsed = json.loads(json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"])
            raw_sugs = parsed.get("suggestions") or []
            out = []
            for idx, item in enumerate(raw_sugs[:5]):
                tid = item.get("template_id")
                if tid not in MOTION_TEMPLATES:
                    continue
                tpl = MOTION_TEMPLATES[tid]
                s_t = max(0.0, float(item.get("start", 0.0)))
                e_t = max(s_t + 2.2, min(s_t + 6.5, float(item.get("end", s_t + 3.4))))
                if out and s_t < out[-1]["end"] + 1.8:
                    continue
                merged = dict(tpl["default_params"])
                for k in ("title", "subtitle", "metric", "visual_prompt"):
                    if item.get(k):
                        merged[k] = str(item[k])[:42 if k != "visual_prompt" else 140]
                if isinstance(item.get("labels"), list) and item["labels"]:
                    merged["labels"] = [str(x)[:18] for x in item["labels"][:4]]
                if isinstance(item.get("points"), list) and item["points"]:
                    merged["points"] = [str(x)[:36] for x in item["points"][:3]]
                if isinstance(item.get("values"), list) and item["values"]:
                    merged["values"] = [float(x) for x in item["values"][:5] if isinstance(x, (int, float))] or merged["values"]
                out.append({
                    "id": f"mg_{idx+1}_{tid}",
                    "start": round(s_t, 2),
                    "end": round(e_t, 2),
                    "excerpt": str(item.get("excerpt") or "")[:140],
                    "subject": str(item.get("subject") or tpl["name"])[:40],
                    "category": tpl["category"],
                    "template_id": tid,
                    "template_name": tpl["name"],
                    "reason": str(item.get("reason") or tpl["description"])[:160],
                    "relevance": "Alta" if str(item.get("relevance", "")).lower().startswith("alt") else "Média",
                    "position": "center",
                    "replace_captions": True,
                    "prompt": merged.get("visual_prompt", ""),
                    "params": merged,
                    "status": "suggested",
                })
            if out:
                return out
        except Exception:
            pass

    # Deterministic speech-to-scene analyzer
    suggestions = []
    last_end = -4.0
    for w in windows:
        if w["s"] - last_end < 3.6:
            continue
        txt = w["text"]
        low = txt.lower()
        has_signal = bool(
            re.search(
                r"triplic|dobr|fatur|receit|lucr|dinheir|r\$|%|cidad|estad|pa[ií]s|mapa|rota|trajet|"
                r"antes.*depois|diferen|compar|primeiro|segundo|etapa|passo|processo|fluxo|ciclo|"
                r"intelig|ia\b|sistema|dados|painel|\b(19|20)\d{2}\b|\b\d+\b|segredo|motivo|porque|funciona",
                low,
            )
        )
        if not has_signal:
            continue
        scene = _parse_speech_to_scene(txt)
        tid = scene["template_id"]
        dur = round(min(6.0, max(2.4, w["e"] - w["s"])), 2)
        suggestions.append({
            "id": f"mg_{len(suggestions)+1}_{tid}",
            "start": round(w["s"], 2),
            "end": round(w["s"] + dur, 2),
            "excerpt": txt,
            "subject": scene["template_name"],
            "category": scene["category"],
            "template_id": tid,
            "template_name": scene["template_name"],
            "reason": f"Ilustra visualmente o conceito falado ({scene['template_name']}) substituindo a legenda.",
            "relevance": "Alta" if re.search(r"\d|%|triplic|dobr|cidad|antes|passo|ia\b", low) else "Média",
            "position": "center",
            "replace_captions": True,
            "prompt": scene["params"].get("visual_prompt", txt),
            "params": scene["params"],
            "status": "suggested",
        })
        last_end = w["s"] + dur
        if len(suggestions) >= 5:
            break
    return suggestions


def _draw_motion_frame(tpl_id: str, params: dict, prog: float, t_sec: float, w: int, h: int, fonts: dict) -> Image.Image:
    """Render one richly detailed, template-distinct RGBA Motion Graphic scene."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    accent = _hex_to_rgb(params.get("accent_color", "#22C55E"))
    easing_mode = params.get("easing", "cubic-out")
    entry_mode = params.get("entry_exit", "slide-up")

    enter_p = _ease(min(1.0, prog / 0.16), easing_mode)
    exit_p = _ease(min(1.0, (1.0 - prog) / 0.15), "smooth")
    alpha_env = max(0.0, min(1.0, min(enter_p, exit_p)))
    anim_p = _ease(min(1.0, max(0.0, (prog - 0.04) / 0.72)), easing_mode)

    fg_a = int(255 * alpha_env)
    mut_a = int(205 * alpha_env)
    acc_a = int(250 * alpha_env)
    soft_a = int(68 * alpha_env)

    pad = 16
    dy = int((1.0 - enter_p) * (28 if entry_mode == "slide-up" else 12))
    bx0, by0, bx1, by1 = pad, pad + dy, w - pad, h - pad + dy
    bw, bh = max(120, bx1 - bx0), max(100, by1 - by0)

    # Distinct shell color tint per family
    shell_bg = {
        "money_flow": (18, 15, 8, int(226 * alpha_env)),
        "multi_city_map": (8, 16, 28, int(228 * alpha_env)),
        "route_path": (8, 16, 28, int(228 * alpha_env)),
        "ai_network": (9, 13, 24, int(228 * alpha_env)),
        "data_dashboard": (11, 14, 20, int(232 * alpha_env)),
        "vs_split_card": (12, 13, 18, int(228 * alpha_env)),
    }.get(tpl_id, (10, 18, 14, int(224 * alpha_env)))

    rad = max(22, int(min(bw, bh) * 0.07))
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=rad, fill=shell_bg, outline=(*accent, int(185 * alpha_env)), width=2)

    title = str(params.get("title") or MOTION_TEMPLATES.get(tpl_id, {}).get("name", "Motion"))[:30]
    subtitle = str(params.get("subtitle") or "")[:40]
    metric = str(params.get("metric") or "")[:14]
    labels = [str(x)[:18] for x in (params.get("labels") or ["Etapa 1", "Etapa 2", "Etapa 3"])]
    points = [str(x)[:38] for x in (params.get("points") or ([subtitle] if subtitle else []))]
    vals = [float(v) for v in (params.get("values") or [30, 68, 98]) if isinstance(v, (int, float))] or [35, 70, 100]

    # Header zone
    draw.text((bx0 + 26, by0 + 22), title, font=fonts["title"], fill=(248, 252, 250, fg_a))
    if subtitle:
        draw.text((bx0 + 26, by0 + 58), subtitle, font=fonts["sub"], fill=(176, 204, 188, mut_a))
    if metric and tpl_id not in ("counter_kpi", "donut_share"):
        draw.rounded_rectangle([bx1 - 150, by0 + 18, bx1 - 24, by0 + 58], radius=12, fill=(*accent, int(44 * alpha_env)), outline=(*accent, int(190 * alpha_env)), width=2)
        draw.text((bx1 - 87, by0 + 38), metric, font=fonts["metric_sm"], fill=(*accent, fg_a), anchor="mm")

    # Main visual area + Bottom explanatory points ribbon (replaces captions cleanly!)
    foot_h = 84 if points else 20
    gx0, gy0 = bx0 + 26, by0 + 96
    gx1, gy1 = bx1 - 26, by1 - foot_h - 14
    gw, gh = max(120, gx1 - gx0), max(90, gy1 - gy0)

    # ---- ART DIRECTION 1: REVENUE GROWTH (Exponential grid + glowing bezier milestones) ----
    if tpl_id == "revenue_growth":
        for k in range(4):
            yy = gy0 + int(gh * k / 4.0)
            draw.line([(gx0, yy), (gx1, yy)], fill=(255, 255, 255, int(30 * alpha_env)), width=1)
        draw.line([(gx0, gy1), (gx1, gy1)], fill=(255, 255, 255, int(90 * alpha_env)), width=2)
        cvals = list(vals[:4])
        while len(cvals) < 3:
            cvals.insert(0, max(5.0, round(cvals[0] * 0.48, 1)))
        n_p = len(cvals)
        vmax = max(cvals) or 100.0
        pts = [(gx0 + 20 + int(((gw - 40) * i) / (n_p - 1)), gy1 - int((gh * 0.80) * (cvals[i] / vmax) * anim_p) - 18) for i in range(n_p)]
        poly = pts + [(pts[-1][0], gy1), (pts[0][0], gy1)]
        draw.polygon(poly, fill=(*accent, int(52 * alpha_env)))
        draw.line(pts, fill=(*accent, acc_a), width=6, joint="curve")
        for i, (px, py) in enumerate(pts):
            if anim_p >= i / float(n_p):
                draw.line([(px, py), (px, gy1)], fill=(*accent, int(70 * alpha_env)), width=2)
                draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(255, 255, 255, fg_a), outline=(*accent, acc_a), width=3)
                if i < len(labels):
                    draw.text((px, py - 18), labels[i][:12], font=fonts["sub"], fill=(240, 252, 245, fg_a), anchor="mb")

    # ---- ART DIRECTION 2: MONEY FLOW (3D Golden Coin Stacks -> Transfer Arc -> Vault) ----
    elif tpl_id == "money_flow":
        sx0 = gx0 + 20
        for col_i in range(3):
            cx = sx0 + col_i * 58
            coins = int((2 + col_i * 2) * anim_p) + 1
            for c_idx in range(coins):
                cy = gy1 - 24 - c_idx * 16
                draw.ellipse([cx, cy - 10, cx + 44, cy + 8], fill=(*accent, acc_a), outline=(255, 245, 190, fg_a), width=2)
                draw.text((cx + 22, cy - 1), "$", font=fonts["sub"], fill=(30, 22, 5, fg_a), anchor="mm")
        vx0, vy0, vx1, vy1 = gx0 + int(gw * 0.56), gy0 + int(gh * 0.16), gx1 - 12, gy1 - 16
        draw.rounded_rectangle([vx0, vy0, vx1, vy1], radius=16, fill=(*accent, int(34 * alpha_env)), outline=(*accent, acc_a), width=2)
        draw.text(((vx0 + vx1) // 2, (vy0 + vy1) // 2 - 14), metric or "R$", font=fonts["hero"], fill=(*accent, fg_a), anchor="mm")
        draw.text(((vx0 + vx1) // 2, (vy0 + vy1) // 2 + 28), labels[-1][:16], font=fonts["sub"], fill=(255, 250, 230, fg_a), anchor="mm")
        # Animated flow particles
        p0 = (sx0 + 150, gy0 + int(gh * 0.45))
        p1 = (vx0 - 10, (vy0 + vy1) // 2)
        draw.line([p0, p1], fill=(*accent, int(140 * alpha_env)), width=4)
        dot_u = (t_sec * 1.4) % 1.0
        dx = int(p0[0] + (p1[0] - p0[0]) * dot_u)
        dy_c = int(p0[1] + (p1[1] - p0[1]) * dot_u)
        draw.ellipse([dx - 8, dy_c - 8, dx + 8, dy_c + 8], fill=(255, 255, 255, fg_a))

    # ---- ART DIRECTION 3: BAR CHART (Y-axis + staggered rising bars + value tags) ----
    elif tpl_id == "bar_chart":
        bvals = list(vals[:4])
        while len(bvals) < 2:
            bvals.insert(0, max(5.0, round(bvals[0] * 0.5, 1)))
        n_b = len(bvals)
        vmax = max(bvals) or 100.0
        for g in range(4):
            gy_g = gy0 + 18 + int((gh - 48) * g / 3.0)
            draw.line([(gx0 + 36, gy_g), (gx1, gy_g)], fill=(255, 255, 255, int(30 * alpha_env)), width=1)
        gap = 24
        bar_w = max(30, (gw - 52 - gap * (n_b - 1)) // n_b)
        for i in range(n_b):
            step_p = _ease(min(1.0, max(0.0, (anim_p - i * 0.10) / 0.65)), easing_mode)
            bx = gx0 + 42 + i * (bar_w + gap)
            cur_h = max(10, int((gh - 62) * (bvals[i] / vmax) * step_p))
            by_top = (gy1 - 28) - cur_h
            col = (*accent, acc_a) if i == n_b - 1 else (120, 175, 220, int(165 * alpha_env))
            draw.rounded_rectangle([bx, by_top, bx + bar_w, gy1 - 28], radius=10, fill=col)
            draw.text((bx + bar_w // 2, by_top - 12), f"{int(bvals[i] * step_p)}", font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mb")
            lbl = labels[i] if i < len(labels) else f"#{i+1}"
            draw.text((bx + bar_w // 2, gy1 - 14), lbl[:10], font=fonts["sub"], fill=(205, 225, 240, mut_a), anchor="mm")

    # ---- ART DIRECTION 4: DONUT SHARE (Left thick progress ring + Right breakdown bars) ----
    elif tpl_id == "donut_share":
        cx, cy = gx0 + int(gw * 0.28), (gy0 + gy1) // 2
        rad_c = max(44, int(min(gw * 0.24, gh * 0.42)))
        box = [cx - rad_c, cy - rad_c, cx + rad_c, cy + rad_c]
        draw.arc(box, start=0, end=360, fill=(255, 255, 255, int(35 * alpha_env)), width=16)
        sweep = int((vals[0] / 100.0 if vals[0] <= 100 else 0.82) * 360 * anim_p)
        draw.arc(box, start=-90, end=-90 + sweep, fill=(*accent, acc_a), width=16)
        draw.text((cx, cy), metric[:8], font=fonts["metric_sm"], fill=(255, 255, 255, fg_a), anchor="mm")
        rx0 = gx0 + int(gw * 0.56)
        for i in range(min(3, len(labels))):
            ry = gy0 + 24 + i * int(gh * 0.27)
            pct = min(100, vals[i] if i < len(vals) else max(25, 85 - i * 25))
            draw.text((rx0, ry), labels[i][:18], font=fonts["sub"], fill=(240, 248, 245, fg_a))
            draw.rounded_rectangle([rx0, ry + 24, gx1 - 10, ry + 36], radius=6, fill=(255, 255, 255, int(28 * alpha_env)))
            draw.rounded_rectangle([rx0, ry + 24, rx0 + int((gx1 - 10 - rx0) * (pct / 100.0) * anim_p), ry + 36], radius=6, fill=(*accent, acc_a if i == 0 else mut_a))

    # ---- ART DIRECTION 5 & 6: MAPS & ROUTES (Radar grid, landmasses, curved paths, radar pins) ----
    elif tpl_id in ("multi_city_map", "route_path"):
        for k in range(1, 5):
            draw.line([(gx0, gy0 + int(gh * k / 5)), (gx1, gy0 + int(gh * k / 5))], fill=(120, 185, 255, int(28 * alpha_env)), width=1)
            draw.line([(gx0 + int(gw * k / 5), gy0), (gx0 + int(gw * k / 5), gy1)], fill=(120, 185, 255, int(28 * alpha_env)), width=1)
        # Stylized landmass polygons
        draw.polygon([(gx0 + 30, gy0 + 40), (gx0 + int(gw * 0.42), gy0 + 22), (gx0 + int(gw * 0.48), gy1 - 40), (gx0 + 50, gy1 - 24)], fill=(45, 90, 130, int(75 * alpha_env)))
        draw.polygon([(gx0 + int(gw * 0.55), gy0 + 55), (gx1 - 30, gy0 + 34), (gx1 - 45, gy1 - 30), (gx0 + int(gw * 0.62), gy1 - 22)], fill=(45, 90, 130, int(75 * alpha_env)))
        n_pins = 2 if tpl_id == "route_path" else max(2, min(3, len(labels)))
        pin_pts = [
            (gx0 + int(gw * (0.18 if n_pins == 2 else (0.18 + 0.32 * i))), gy0 + int(gh * (0.64 if i % 2 == 0 else 0.30)))
            for i in range(n_pins)
        ]
        if n_pins == 2:
            pin_pts[1] = (gx0 + int(gw * 0.80), gy0 + int(gh * 0.32))
        for i in range(len(pin_pts) - 1):
            p0, p1 = pin_pts[i], pin_pts[i + 1]
            # Curved arc points
            arc_pts = []
            steps = 20
            max_st = max(1, int(steps * anim_p))
            for s_i in range(max_st + 1):
                u = s_i / float(steps)
                ax = int(p0[0] + (p1[0] - p0[0]) * u)
                ay = int(p0[1] + (p1[1] - p0[1]) * u - 46 * math.sin(math.pi * u))
                arc_pts.append((ax, ay))
            if len(arc_pts) >= 2:
                draw.line(arc_pts, fill=(*accent, acc_a), width=4)
                hx, hy = arc_pts[-1]
                draw.ellipse([hx - 7, hy - 7, hx + 7, hy + 7], fill=(255, 255, 255, fg_a))
        for i, (px, py) in enumerate(pin_pts):
            pulse = 14 + int(8 * abs(math.sin(t_sec * 4.2 + i)))
            draw.ellipse([px - pulse, py - pulse, px + pulse, py + pulse], outline=(*accent, int(130 * alpha_env)), width=2)
            draw.ellipse([px - 9, py - 9, px + 9, py + 9], fill=(*accent, fg_a), outline=(255, 255, 255, fg_a), width=2)
            lbl = labels[i][:14] if i < len(labels) else f"Ponto {i+1}"
            draw.rounded_rectangle([px - 56, py + 14, px + 56, py + 38], radius=8, fill=(8, 16, 28, int(220 * alpha_env)), outline=(*accent, int(140 * alpha_env)), width=1)
            draw.text((px, py + 26), lbl, font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")

    # ---- ART DIRECTION 7: AI NETWORK (Central Hexagonal Core + Orbital Rings + Synapses) ----
    elif tpl_id == "ai_network":
        cx, cy = gx0 + int(gw * 0.40), (gy0 + gy1) // 2
        for r_ring in (52, 76):
            draw.ellipse([cx - r_ring, cy - r_ring, cx + r_ring, cy + r_ring], outline=(*accent, int(90 * alpha_env)), width=2)
        rot = t_sec * 1.6
        sat_pts = [(cx + int(115 * math.cos(rot + k * 1.25)), cy + int(82 * math.sin(rot + k * 1.25))) for k in range(5)]
        for sx, sy in sat_pts:
            draw.line([(cx, cy), (sx, sy)], fill=(*accent, int(120 * alpha_env)), width=2)
            draw.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], fill=(255, 255, 255, fg_a), outline=(*accent, acc_a), width=2)
        draw.regular_polygon((cx, cy, 36), n_sides=6, rotation=t_sec * 25, fill=(*accent, int(80 * alpha_env)), outline=(*accent, fg_a))
        draw.text((cx, cy), "IA", font=fonts["metric_sm"], fill=(255, 255, 255, fg_a), anchor="mm")
        # Concept nodes stacked on right
        rx0 = gx0 + int(gw * 0.68)
        for i in range(min(3, len(labels))):
            ny = gy0 + 20 + i * int(gh * 0.28)
            draw.rounded_rectangle([rx0, ny, gx1 - 6, ny + 38], radius=10, fill=(255, 255, 255, int(22 * alpha_env)), outline=(*accent, int(160 * alpha_env)), width=1)
            draw.text((rx0 + 12, ny + 19), labels[i][:15], font=fonts["sub"], fill=(245, 250, 255, fg_a), anchor="lm")

    # ---- ART DIRECTION 8: DATA DASHBOARD (Window Dots + Equalizer + Sparkline) ----
    elif tpl_id == "data_dashboard":
        draw.rounded_rectangle([gx0, gy0, gx1, gy1], radius=14, fill=(18, 24, 34, int(190 * alpha_env)), outline=(255, 255, 255, int(45 * alpha_env)), width=1)
        for d_i, dc in enumerate(((244, 63, 94), (250, 204, 21), (34, 197, 94))):
            draw.ellipse([gx0 + 16 + d_i * 18, gy0 + 12, gx0 + 26 + d_i * 18, gy0 + 22], fill=(*dc, fg_a))
        # Audio/data equalizer bars
        eq_x = gx0 + 24
        for e_i in range(12):
            bh_e = 14 + int(36 * abs(math.sin(t_sec * 5.0 + e_i * 0.7)) * anim_p)
            bx_e = eq_x + e_i * 18
            draw.rounded_rectangle([bx_e, gy0 + 82 - bh_e, bx_e + 11, gy0 + 82], radius=3, fill=(*accent, acc_a))
        # Labels grid inside panel
        for i, lbl in enumerate(labels[:3]):
            cx_b = gx0 + 24 + i * ((gw - 64) // max(1, len(labels[:3])))
            draw.rounded_rectangle([cx_b, gy0 + 102, cx_b + 148, gy1 - 16], radius=10, fill=(*accent, int(30 * alpha_env)), outline=(*accent, int(130 * alpha_env)), width=1)
            draw.text((cx_b + 74, (gy0 + 102 + gy1 - 16) // 2), lbl[:14], font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")

    # ---- ART DIRECTION 9: VS SPLIT CARD (Red vs Green Duel Comparison) ----
    elif tpl_id == "vs_split_card":
        mid_x = (gx0 + gx1) // 2
        draw.rounded_rectangle([gx0, gy0 + 6, mid_x - 16, gy1 - 6], radius=14, fill=(239, 68, 68, int(36 * alpha_env)), outline=(239, 68, 68, int(170 * alpha_env)), width=2)
        draw.rounded_rectangle([mid_x + 16, gy0 + 6, gx1, gy1 - 6], radius=14, fill=(*accent, int(40 * alpha_env)), outline=(*accent, int(190 * alpha_env)), width=2)
        draw.text(((gx0 + mid_x - 16) // 2, gy0 + 36), f"[-] {labels[0][:14]}", font=fonts["title_sm"], fill=(252, 165, 165, fg_a), anchor="mm")
        r_lbl = labels[1] if len(labels) > 1 else "Novo"
        draw.text(((mid_x + 16 + gx1) // 2, gy0 + 36), f"[+] {r_lbl[:14]}", font=fonts["title_sm"], fill=(134, 239, 172, fg_a), anchor="mm")
        if points:
            draw.text(((gx0 + mid_x - 16) // 2, (gy0 + gy1) // 2 + 12), points[0][:20], font=fonts["sub"], fill=(255, 225, 225, fg_a), anchor="mm")
            r_pt = points[1] if len(points) > 1 else "Melhor resultado"
            draw.text(((mid_x + 16 + gx1) // 2, (gy0 + gy1) // 2 + 12), r_pt[:20], font=fonts["sub"], fill=(230, 255, 240, fg_a), anchor="mm")
        draw.ellipse([mid_x - 24, (gy0 + gy1) // 2 - 24, mid_x + 24, (gy0 + gy1) // 2 + 24], fill=(15, 23, 20, fg_a), outline=(255, 255, 255, fg_a), width=2)
        draw.text((mid_x, (gy0 + gy1) // 2), "VS", font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")

    # ---- ART DIRECTION 10: FLOW DIAGRAM / TIMELINE (Illuminated Sequential Nodes) ----
    elif tpl_id in ("flow_diagram", "timeline_steps"):
        n_st = max(2, min(3, len(labels)))
        step_w = max(90, (gw - 48 * (n_st - 1)) // n_st)
        cy = (gy0 + gy1) // 2
        if n_st >= 2:
            line_end = gx0 + step_w // 2 + int((gw - step_w) * anim_p)
            draw.line([(gx0 + step_w // 2, cy), (line_end, cy)], fill=(*accent, acc_a), width=5)
        for i in range(n_st):
            sx0 = gx0 + i * (step_w + 48)
            lit = anim_p >= (i / float(n_st))
            fill_c = (*accent, int(68 * alpha_env)) if lit else (255, 255, 255, int(18 * alpha_env))
            brd_c = (*accent, acc_a) if lit else (255, 255, 255, int(75 * alpha_env))
            draw.rounded_rectangle([sx0, cy - 42, sx0 + step_w, cy + 48], radius=14, fill=fill_c, outline=brd_c, width=2)
            draw.ellipse([sx0 + step_w // 2 - 14, cy - 56, sx0 + step_w // 2 + 14, cy - 28], fill=(*accent, acc_a if lit else mut_a))
            draw.text((sx0 + step_w // 2, cy - 42), f"0{i+1}", font=fonts["sub"], fill=(8, 16, 12, fg_a), anchor="mm")
            lbl_st = labels[i] if i < len(labels) else f"Etapa {i+1}"
            draw.text((sx0 + step_w // 2, cy + 10), lbl_st[:15], font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")

    # ---- ART DIRECTION 11: CYCLE LOOP (3-Node Equilateral Orbital Triangle) ----
    elif tpl_id == "cycle_loop":
        cx, cy = (gx0 + gx1) // 2, (gy0 + gy1) // 2 + 6
        rad_l = max(46, int(min(gw, gh) * 0.36))
        draw.arc([cx - rad_l, cy - rad_l, cx + rad_l, cy + rad_l], start=0, end=360, fill=(255, 255, 255, int(40 * alpha_env)), width=4)
        ang_head = -90 + int(360 * anim_p)
        draw.arc([cx - rad_l, cy - rad_l, cx + rad_l, cy + rad_l], start=-90, end=ang_head, fill=(*accent, acc_a), width=6)
        node_angles = (-90, 30, 150)
        for i, ang in enumerate(node_angles):
            nx = cx + int(rad_l * math.cos(math.radians(ang)))
            ny = cy + int(rad_l * math.sin(math.radians(ang)))
            draw.rounded_rectangle([nx - 64, ny - 18, nx + 64, ny + 18], radius=10, fill=(14, 20, 28, int(235 * alpha_env)), outline=(*accent, acc_a), width=2)
            draw.text((nx, ny), (labels[i] if i < len(labels) else f"Fase {i+1}")[:14], font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")

    # ---- ART DIRECTION 12: COUNTER KPI / BEFORE-AFTER / CONCEPT / BADGE ----
    elif tpl_id == "before_after_meter":
        for i in range(2):
            ry = gy0 + 26 + i * 74
            pct = (vals[i] if i < len(vals) else (30 if i == 0 else 95)) / 100.0
            draw.text((gx0, ry), (labels[i] if i < len(labels) else ("Antes" if i == 0 else "Depois"))[:24], font=fonts["sub"], fill=(240, 248, 244, fg_a))
            draw.rounded_rectangle([gx0, ry + 26, gx1, ry + 50], radius=10, fill=(255, 255, 255, int(28 * alpha_env)))
            bar_c = (245, 158, 11, acc_a) if i == 0 else (*accent, acc_a)
            draw.rounded_rectangle([gx0, ry + 26, gx0 + max(24, int(gw * min(1.0, pct) * anim_p)), ry + 50], radius=10, fill=bar_c)
    elif tpl_id == "counter_kpi":
        cx, cy = (gx0 + gx1) // 2, (gy0 + gy1) // 2
        m_num = re.findall(r"\d+", metric)
        center_txt = metric
        if m_num:
            target_n = int(m_num[0])
            center_txt = metric.replace(m_num[0], str(int(target_n * anim_p)), 1)
        draw.rounded_rectangle([cx - 170, cy - 52, cx + 170, cy + 52], radius=20, fill=(*accent, int(36 * alpha_env)), outline=(*accent, acc_a), width=3)
        draw.text((cx, cy), center_txt[:12], font=fonts["hero"], fill=(255, 255, 255, fg_a), anchor="mm")
    else:
        # concept_callout / badge_alert: highlighter sweep + checklist points
        cx, cy = (gx0 + gx1) // 2, gy0 + int(gh * 0.32)
        hl_w = int(gw * 0.78 * anim_p)
        draw.rounded_rectangle([cx - gw * 0.39, cy - 26, cx - gw * 0.39 + max(20, hl_w), cy + 26], radius=12, fill=(*accent, int(85 * alpha_env)))
        draw.text((cx, cy), (labels[0] if labels else title)[:24], font=fonts["title"], fill=(255, 255, 255, fg_a), anchor="mm")
        for i, pt in enumerate(points[:2]):
            py_p = gy0 + int(gh * 0.68) + i * 32
            if anim_p >= 0.35 + i * 0.25:
                draw.text((gx0 + 18, py_p), f"+  {pt[:34]}", font=fonts["sub"], fill=(225, 245, 232, fg_a), anchor="lm")

    # Bottom explanatory callout strip (replaces ASS captions cleanly)
    if points:
        fy0 = by1 - foot_h
        draw.rounded_rectangle([bx0 + 18, fy0, bx1 - 18, by1 - 14], radius=14, fill=(255, 255, 255, int(18 * alpha_env)), outline=(*accent, int(90 * alpha_env)), width=1)
        idx_pt = min(len(points) - 1, int(prog * len(points)))
        active_pt = points[idx_pt]
        draw.text(((bx0 + bx1) // 2, (fy0 + by1 - 14) // 2), active_pt[:38], font=fonts["title_sm"], fill=(255, 255, 255, fg_a), anchor="mm")

    return img


def render_motion_clip(
    template_id: str,
    params: dict,
    out_path: Path,
    duration: float = 3.2,
    width: int = 780,
    height: int = 530,
    fps: int = 24,
    on_progress=None,
    cancel_event=None,
) -> Path:
    """Render parameterized explanatory Motion Graphic into a lossless RGBA .mov overlay clip."""
    from processor import find_ffmpeg

    ffmpeg, _ = find_ffmpeg()
    tpl = MOTION_TEMPLATES.get(template_id, MOTION_TEMPLATES["revenue_growth"])
    merged = dict(tpl["default_params"])
    merged.update(params or {})

    dur = max(1.2, min(10.0, float(duration or 3.2)))
    speed = max(0.5, min(2.0, float(merged.get("speed", 1.0))))
    w = max(320, int(width) - (int(width) % 2))
    h = max(220, int(height) - (int(height) % 2))
    total_frames = max(12, int(round(dur * fps)))

    sc = w / 780.0
    fonts = {
        "title": _load_font("CreatoDisplay-ExtraBold.otf", int(30 * sc)),
        "title_sm": _load_font("CreatoDisplay-Bold.otf", int(22 * sc)),
        "sub": _load_font("CreatoDisplay-Regular.otf", int(18 * sc)),
        "metric_sm": _load_font("CreatoDisplay-ExtraBold.otf", int(24 * sc)),
        "hero": _load_font("CreatoDisplay-ExtraBold.otf", int(48 * sc)),
    }

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    log_path = Path(out_path).with_suffix(".ffmpeg.log")
    cmd = [
        ffmpeg, "-y",
        "-f", "image2pipe", "-vcodec", "png", "-r", str(fps), "-i", "-",
        "-an", "-vcodec", "png", "-pix_fmt", "rgba",
        str(out_path),
    ]
    with open(log_path, "wb") as lf:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=lf)
        try:
            for f_idx in range(total_frames):
                if cancel_event is not None and cancel_event.is_set():
                    proc.kill()
                    raise RuntimeError("Renderização de Motion Graphic cancelada.")
                prog = f_idx / float(max(1, total_frames - 1))
                t_sec = (f_idx / float(fps)) * speed
                frame = _draw_motion_frame(template_id, merged, prog, t_sec, w, h, fonts)
                frame.save(proc.stdin, format="PNG", compress_level=1)
                if on_progress and (f_idx % max(1, total_frames // 8) == 0 or f_idx == total_frames - 1):
                    on_progress(int(10 + 85 * ((f_idx + 1) / float(total_frames))))
            proc.stdin.close()
            rc = proc.wait(timeout=45)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            raise
    if rc != 0:
        err_txt = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""
        try:
            log_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(f"Erro FFmpeg Motion Worker: {err_txt[-300:]}")
    try:
        log_path.unlink(missing_ok=True)
    except Exception:
        pass
    return Path(out_path)
