"""
Eu Edito — Motion Director v3 (Face-Safe, Script-Driven, 2x Vector & Kinetic Engine)
Creates bespoke, self-explanatory Motion Graphics directly from what the speaker says
in the script (or user prompt) — NEVER generic template titles or clunky boxy cards.
Designed for floating Lower-Third / Face-Safe transparent composition with bundled
creator typography, Gaussian glow bloom, and 20+ animated vector scenes.
"""
import json
import math
import os
import re
import subprocess
import textwrap
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

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

MOOD_PALETTES = {
    "emerald": "#22C55E",
    "gold": "#FACC15",
    "cyan": "#38BDF8",
    "violet": "#A855F7",
    "coral": "#FB7185",
    "amber": "#F59E0B",
    "mint": "#34D399",
}

MOTION_TEMPLATES = {
    "sketch_calligraphy": {
        "id": "sketch_calligraphy",
        "category": "educacao",
        "name": "Papel & Traço Animado",
        "description": "Folha flutuante com caneta desenhando traço ao vivo e título do roteiro.",
        "default_params": {
            "title": "Conteúdo Prático",
            "accent_text": "para aplicar",
            "subtitle": "Material organizado em etapas",
            "values": [100],
            "labels": ["Pronto", "Prático", "PDF"],
            "points": ["Material direto para usar no dia a dia"],
            "metric": "PRÁTICO",
            "icon": "pen",
            "accent_color": "#38BDF8",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "slide-up",
        },
    },
    "kinetic_timer": {
        "id": "kinetic_timer",
        "category": "elementos",
        "name": "Relógio & Rotina Cinética",
        "description": "Cronômetro luminoso animado com contagem e rotina diária.",
        "default_params": {
            "title": "Rotina Rápida",
            "accent_text": "por dia",
            "subtitle": "Pouco tempo, resultado constante",
            "values": [10],
            "labels": ["Seg", "Ter", "Qua", "Qui"],
            "points": ["Constância diária sem complicação"],
            "metric": "10 MIN",
            "icon": "clock",
            "accent_color": "#FACC15",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
        },
    },
    "rocket_boost": {
        "id": "rocket_boost",
        "category": "negocios",
        "name": "Decolagem & Escala",
        "description": "Foguete vetorial decolando com rastro luminoso e destaque da meta.",
        "default_params": {
            "title": "Salto de Escala",
            "accent_text": "acelerada",
            "subtitle": "Impulso real citado na fala",
            "values": [20, 55, 100],
            "labels": ["Base", "Impulso", "Escala"],
            "points": ["Crescimento acelerado com consistência"],
            "metric": "3X+",
            "icon": "rocket",
            "accent_color": "#22C55E",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "slide-up",
        },
    },
    "checklist_reveal": {
        "id": "checklist_reveal",
        "category": "educacao",
        "name": "Checklist Iluminado",
        "description": "Itens reais do roteiro entrando com marcação vetorial animada.",
        "default_params": {
            "title": "Pontos-Chave",
            "accent_text": "na prática",
            "subtitle": "Resumo objetivo da explicação",
            "values": [1, 2, 3],
            "labels": ["Item 1", "Item 2", "Item 3"],
            "points": ["Aplicação clara passo a passo"],
            "metric": "CHECK",
            "icon": "check",
            "accent_color": "#34D399",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "revenue_growth": {
        "id": "revenue_growth",
        "category": "negocios",
        "name": "Curva Neon Flutuante",
        "description": "Curva ascendente sem caixa pesada, com rastro de luz e marcos da fala.",
        "default_params": {
            "title": "Evolução Real",
            "accent_text": "em alta",
            "subtitle": "Crescimento citado no vídeo",
            "values": [22, 46, 74, 100],
            "labels": ["Início", "Avanço", "Escala", "Topo"],
            "points": ["Tendência crescente destacada"],
            "metric": "+300%",
            "icon": "chart",
            "accent_color": "#22C55E",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "money_flow": {
        "id": "money_flow",
        "category": "negocios",
        "name": "Moedas & Fluxo de Valor",
        "description": "Moedas 3D com brilho e partículas ligadas ao valor citado.",
        "default_params": {
            "title": "Retorno Direto",
            "accent_text": "em valor",
            "subtitle": "Movimentação financeira da fala",
            "values": [38, 72, 100],
            "labels": ["Entrada", "Fluxo", "Caixa"],
            "points": ["Resultado financeiro claro"],
            "metric": "R$",
            "icon": "coin",
            "accent_color": "#FACC15",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "bar_chart": {
        "id": "bar_chart",
        "category": "graficos",
        "name": "Colunas Flutuantes",
        "description": "Colunas de vidro com topo luminoso e valores suspensos.",
        "default_params": {
            "title": "Comparativo",
            "accent_text": "dos números",
            "subtitle": "Proporção real citada",
            "values": [28, 56, 94],
            "labels": ["Etapa 1", "Etapa 2", "Atual"],
            "points": ["Evolução comparada por marco"],
            "metric": "DADOS",
            "icon": "chart",
            "accent_color": "#38BDF8",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "donut_share": {
        "id": "donut_share",
        "category": "graficos",
        "name": "Anel de Proporção",
        "description": "Anel vetorial luminoso com porcentagem e barras flutuantes.",
        "default_params": {
            "title": "Participação",
            "accent_text": "em destaque",
            "subtitle": "Divisão citada no trecho",
            "values": [78, 22],
            "labels": ["Principal", "Restante"],
            "points": ["Proporção principal do tema"],
            "metric": "78%",
            "icon": "target",
            "accent_color": "#A855F7",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
        },
    },
    "multi_city_map": {
        "id": "multi_city_map",
        "category": "mapas",
        "name": "Globo & Pinos no Mapa",
        "description": "Radar circular translúcido com arcos de voo e pinos pulsantes.",
        "default_params": {
            "title": "Conexão Local",
            "accent_text": "no mapa",
            "subtitle": "Regiões mencionadas na fala",
            "values": [1, 2, 3],
            "labels": ["Origem", "Escala", "Destino"],
            "points": ["Expansão geográfica destacada"],
            "metric": "MAPA",
            "icon": "pin",
            "accent_color": "#38BDF8",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "route_path": {
        "id": "route_path",
        "category": "mapas",
        "name": "Trajeto Ponto A → B",
        "description": "Arco luminoso conectando origem e destino citados na fala.",
        "default_params": {
            "title": "Rota Direta",
            "accent_text": "do trajeto",
            "subtitle": "Caminho do início ao destino",
            "values": [1, 2],
            "labels": ["Saída", "Chegada"],
            "points": ["Deslocamento direto entre pontos"],
            "metric": "ROTA",
            "icon": "pin",
            "accent_color": "#22C55E",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "smooth",
            "entry_exit": "slide-up",
        },
    },
    "ai_network": {
        "id": "ai_network",
        "category": "tecnologia",
        "name": "Órbita Digital & IA",
        "description": "Esferas orbitais e núcleo de automação para temas de tecnologia.",
        "default_params": {
            "title": "Automação Inteligente",
            "accent_text": "em rede",
            "subtitle": "Conexões digitais do processo",
            "values": [95],
            "labels": ["Entrada", "Motor", "Saída"],
            "points": ["Processamento conectado em tempo real"],
            "metric": "IA",
            "icon": "brain",
            "accent_color": "#38BDF8",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "data_dashboard": {
        "id": "data_dashboard",
        "category": "tecnologia",
        "name": "HUD & Painel ao Vivo",
        "description": "Interface translúcida com espectro animado e status do sistema.",
        "default_params": {
            "title": "Sistema Ativo",
            "accent_text": "em operação",
            "subtitle": "Métricas dinâmicas",
            "values": [42, 68, 86, 98],
            "labels": ["Rápido", "Ativo"],
            "points": ["Operação contínua automatizada"],
            "metric": "LIVE",
            "icon": "bolt",
            "accent_color": "#34D399",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "timeline_steps": {
        "id": "timeline_steps",
        "category": "educacao",
        "name": "Trilha de Evolução",
        "description": "Pílulas sequenciais luminosas com feixe de progresso.",
        "default_params": {
            "title": "Jornada Clara",
            "accent_text": "etapa por etapa",
            "subtitle": "Sequência explicada no trecho",
            "values": [1, 2, 3],
            "labels": ["Início", "Prática", "Resultado"],
            "points": ["Evolução contínua ao longo do tempo"],
            "metric": "ETAPAS",
            "icon": "calendar",
            "accent_color": "#F59E0B",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "concept_callout": {
        "id": "concept_callout",
        "category": "educacao",
        "name": "Tipografia & Ícone Hero",
        "description": "Composição editorial flutuante com ícone vetorial animado e marca-texto.",
        "default_params": {
            "title": "Ideia Principal",
            "accent_text": "em foco",
            "subtitle": "Explicação direta do vídeo",
            "values": [100],
            "labels": ["Essencial", "Prático"],
            "points": ["Síntese clara da fala"],
            "metric": "FOCO",
            "icon": "bulb",
            "accent_color": "#38BDF8",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "vs_split_card": {
        "id": "vs_split_card",
        "category": "comparacoes",
        "name": "Contraste Dinâmico (VS)",
        "description": "Dois cartões flutuantes em oposição ligados por raio luminoso.",
        "default_params": {
            "title": "Dois Cenários",
            "accent_text": "em contraste",
            "subtitle": "Comparação direta da fala",
            "values": [25, 95],
            "labels": ["Antes", "Agora"],
            "points": ["Diferença prática entre os dois lados"],
            "metric": "VS",
            "icon": "bolt",
            "accent_color": "#22C55E",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "slide-up",
        },
    },
    "before_after_meter": {
        "id": "before_after_meter",
        "category": "comparacoes",
        "name": "Medidor de Salto",
        "description": "Barras flutuantes de comparação mostrando evolução de nível.",
        "default_params": {
            "title": "Mudança de Nível",
            "accent_text": "comparada",
            "subtitle": "Antes vs Novo padrão",
            "values": [28, 92],
            "labels": ["Antes", "Depois"],
            "points": ["Salto expressivo de resultado"],
            "metric": "+3X",
            "icon": "trophy",
            "accent_color": "#22C55E",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
        },
    },
    "flow_diagram": {
        "id": "flow_diagram",
        "category": "processos",
        "name": "Fluxo Conectado",
        "description": "Blocos de vidro sequenciais conectados por pulso de energia.",
        "default_params": {
            "title": "Como Funciona",
            "accent_text": "passo a passo",
            "subtitle": "Processo citado na fala",
            "values": [1, 2, 3],
            "labels": ["Passo 1", "Passo 2", "Passo 3"],
            "points": ["Sequência prática de execução"],
            "metric": "FLUXO",
            "icon": "spark",
            "accent_color": "#22C55E",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
        },
    },
    "cycle_loop": {
        "id": "cycle_loop",
        "category": "processos",
        "name": "Órbita Contínua",
        "description": "Anel orbital animado ligando 3 fases que se retroalimentam.",
        "default_params": {
            "title": "Ciclo Contínuo",
            "accent_text": "sem parar",
            "subtitle": "Engrenagem do método",
            "values": [3],
            "labels": ["Ação", "Efeito", "Escala"],
            "points": ["Movimento circular constante"],
            "metric": "CICLO",
            "icon": "target",
            "accent_color": "#A855F7",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "smooth",
            "entry_exit": "fade",
        },
    },
    "counter_kpi": {
        "id": "counter_kpi",
        "category": "elementos",
        "name": "Número Cinético Gigante",
        "description": "Contagem progressiva com halo radial e frase do roteiro.",
        "default_params": {
            "title": "Marco Citado",
            "accent_text": "em números",
            "subtitle": "Dado de impacto do vídeo",
            "values": [100],
            "labels": ["Impacto"],
            "points": ["Número central da explicação"],
            "metric": "100%",
            "icon": "trophy",
            "accent_color": "#FACC15",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
    "badge_alert": {
        "id": "badge_alert",
        "category": "elementos",
        "name": "Alerta Editorial Pulsante",
        "description": "Selo de atenção animado com destaque editorial e ponto-chave.",
        "default_params": {
            "title": "Atenção Nisso",
            "accent_text": "agora",
            "subtitle": "Alerta citado na fala",
            "values": [100],
            "labels": ["Importante"],
            "points": ["Ponto que merece cuidado"],
            "metric": "!",
            "icon": "bolt",
            "accent_color": "#FB7185",
            "position": "bottom-card",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
        },
    },
}

AVAILABLE_ICONS = (
    "pen", "clock", "rocket", "coin", "chart", "pin", "bolt",
    "check", "bulb", "target", "book", "trophy", "flame", "calendar",
    "brain", "spark",
)


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
        if t < 0.68:
            u = t / 0.68
            return 1.08 * (1.0 - (1.0 - u) ** 3)
        u = (t - 0.68) / 0.32
        return 1.08 - 0.08 * (u * u * (3.0 - 2.0 * u))
    if mode == "smooth":
        return t * t * (3.0 - 2.0 * t)
    return 1.0 - (1.0 - t) ** 3


def _load_font(filename: str, size: int):
    fp = FONTS_DIR / filename
    try:
        if fp.exists():
            return ImageFont.truetype(str(fp), max(12, int(size)))
    except Exception:
        pass
    for fallback in ("CreatoDisplay-Bold.otf", "DMSans.ttf", "BebasNeue-Regular.ttf"):
        fp2 = FONTS_DIR / fallback
        if fp2.exists():
            try:
                return ImageFont.truetype(str(fp2), max(12, int(size)))
            except Exception:
                pass
    return ImageFont.load_default()


def _clean_clauses(text: str, max_items: int = 3, max_chars: int = 26) -> list:
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


def _extract_script_headline(text: str) -> tuple:
    """
    Build a punchy (headline, accent_text, subtitle) directly from spoken PT-BR words
    instead of using static template names.
    """
    raw = re.sub(r"\s+", " ", (text or "").strip()).strip(" .!?")
    if not raw:
        return ("Destaque da Fala", "", "")

    stripped = re.sub(
        r"^(?:então|olha só|olha|veja bem|é uma|é um|isso é|esse é|essa é|aqui tem|"
        r"a gente faz|a gente|nós fazemos|você faz|você pode|porque nós|porque)\s+",
        "",
        raw,
        flags=re.I,
    ).strip()
    words = stripped.split()
    if len(words) <= 2:
        return (stripped.title()[:28], "", raw[:44])

    # Look for a prepositional/italic split ("de ...", "para ...", "por ...", "em ...", "com ...")
    split_idx = None
    for i in range(1, min(len(words), 5)):
        if words[i].lower() in ("para", "por", "sem", "com", "em", "até", "no", "na") and i >= 2:
            split_idx = i
            break

    if split_idx is not None:
        head = " ".join(words[:split_idx]).strip()
        acc = " ".join(words[split_idx : split_idx + 3]).strip(".,!?")
    else:
        head = " ".join(words[: min(3, len(words))]).strip(".,!?")
        acc = " ".join(words[min(3, len(words)) : min(6, len(words))]).strip(".,!?")

    # Drop dangling stop-word at end of head and truncate cleanly at word boundaries (NEVER mid-word!)
    head_w = head.split()
    while len(head_w) > 1 and head_w[-1].lower() in ("de", "do", "da", "e", "o", "a", "um", "uma", "em"):
        acc = f"{head_w.pop()} {acc}".strip()
    head = " ".join(head_w)
    wrapped_h = textwrap.wrap(head, width=24, break_long_words=False)
    head_clean = wrapped_h[0] if wrapped_h else head[:24]
    wrapped_a = textwrap.wrap(acc, width=22, break_long_words=False)
    acc_clean = wrapped_a[0] if wrapped_a else acc[:22]
    return (head_clean.upper(), acc_clean.lower(), raw[:44])


def _pick_icon_from_text(low: str, tid: str) -> str:
    if re.search(r"caligraf|escrev|letra|caderno|papel|imprim|pdf|folha|desenh|caneta", low):
        return "pen"
    if re.search(r"minut|hora|segundo|tempo|dia|rápid|rel[oó]g|prazo", low):
        return "clock"
    if re.search(r"decol|foguete|explod|dispar|lan[çc]am", low):
        return "rocket"
    if re.search(r"dinheir|r\$|reais|lucr|caixa|pag|moeda|riquez|ganh", low):
        return "coin"
    if re.search(r"fatur|cresc|escal|gr[aá]fic|m[eé]trica|venda", low):
        return "chart"
    if re.search(r"cidad|estad|pa[ií]s|mapa|rota|viag|lugar|local", low):
        return "pin"
    if re.search(r"\bia\b|intelig[eê]ncia|neural|algoritm", low):
        return "brain"
    if re.search(r"livro|estud|curso|aul[ao]|aprender|ensinar|leitur", low):
        return "book"
    if re.search(r"erro|cuidado|aten[çc]|nunca|proibid|urgente|r[aá]pid", low):
        return "bolt"
    if re.search(r"camp[eã]|pr[eê]mio|record|topo|melhor|vencer|sucesso", low):
        return "trophy"
    if re.search(r"meta|objetiv|foco|alvo|acertar", low):
        return "target"
    if re.search(r"fogo|viral|quente|tend[eê]nc|boom", low):
        return "flame"
    return MOTION_TEMPLATES.get(tid, {}).get("default_params", {}).get("icon", "spark")


def _parse_speech_to_scene(text: str, preferred_tid: str = None) -> dict:
    """Turn spoken text or prompt into bespoke script-grounded Motion scene parameters."""
    txt = re.sub(r"\s+", " ", (text or "").strip())
    low = txt.lower()
    nums = re.findall(r"r\$\s*[\d.,]+(?:\s*(?:mil|mi|bi|m|k))?|\d+(?:[.,]\d+)?\s*%|\b\d+(?:[.,]\d+)?\b", txt, re.I)

    tid = preferred_tid if preferred_tid in MOTION_TEMPLATES else None
    if not tid:
        if re.search(r"caligraf|escrev|letra|caderno|imprim|pdf|folha|apostil|desenh", low):
            tid = "sketch_calligraphy"
        elif re.search(r"(?:dez|vinte|trinta|cinco|\d+)\s*minut|\bpor dia\b|\btodos os dias\b|tempo|rel[oó]g|hora", low):
            tid = "kinetic_timer"
        elif re.search(r"decol|lan[çc]am|dispar|explod", low):
            tid = "rocket_boost"
        elif re.search(r"triplic|dobr|quadruplic|faturament|receit|venda|cresc|escal", low):
            tid = "revenue_growth"
        elif re.search(r"r\$|reais|dinheir|invest|lucr|pag|ganh", low):
            tid = "money_flow"
        elif re.search(r"rota|trajet|viag|caminh|saindo|chegando|indo para", low):
            tid = "route_path"
        elif re.search(r"cidad|estad|pa[ií]s|regi[aã]o|local|mapa|lugares|brasil", low):
            tid = "multi_city_map"
        elif re.search(r"antes.*depois|em vez|enquanto|compar|melhor.*que|pior.*que|\bvs\b|versus|diferen", low):
            tid = "vs_split_card"
        elif re.search(r"ciclo|gira|volta|loop|cont[ií]nu", low):
            tid = "cycle_loop"
        elif re.search(r"primeiro|segundo|terceiro|etapa|passo|processo|fluxo|mecanism", low):
            tid = "flow_diagram"
        elif re.search(r"lista|benef[ií]cio|vantagen|inclui|itens|check|garant", low):
            tid = "checklist_reveal"
        elif re.search(r"\bintelig[eê]ncia\b|\bia\b|algoritm|neural|\bautom", low):
            tid = "ai_network"
        elif re.search(r"sistema|aplicativo|painel|dados|\btela\b|plataforma|\bapp\b", low):
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

    head, accent_text, full_sub = _extract_script_headline(txt)
    icon = _pick_icon_from_text(low, tid)
    metric = ""
    labels = []
    values = list(merged["values"])
    points = _clean_clauses(txt, max_items=2, max_chars=36)

    # Multi-word proper nouns (places, names)
    tail_txt = " ".join(txt.split()[1:]) if len(txt.split()) > 1 else ""
    cap_words = [
        m.strip(".,!?;:")
        for m in re.findall(r"\b[A-ZÀ-Ú][a-zà-ú]{1,}(?:\s+[A-ZÀ-Ú][a-zà-ú]{1,})*", tail_txt)
        if m.lower() not in ("agora", "antes", "depois", "passo", "hoje", "então", "isso")
    ]

    word_num_map = {"um": "1", "dois": "2", "três": "3", "tres": "3", "cinco": "5", "dez": "10", "vinte": "20", "trinta": "30"}
    spoken_num = None
    for wn, dg in word_num_map.items():
        if re.search(rf"\b{wn}\b", low):
            spoken_num = dg
            break

    if tid == "sketch_calligraphy":
        kw = [w.strip(".,!?") for w in re.findall(r"\b(?:caligrafia|cursiva|imprimir|pdf|coleção|caderno|prático|infantil|treino)\b", low)]
        labels = list(dict.fromkeys([k.capitalize() for k in kw]))[:3] or ["Folhas", "Treino", "Imprimir"]
        metric = "IMPRIMIR" if "imprim" in low else (kw[0].upper()[:8] if kw else "GUIA")
    elif tid == "kinetic_timer":
        n_m = nums[0] if nums else (spoken_num or "10")
        unit = "MIN" if "minut" in low else ("H" if "hora" in low else "DIAS")
        metric = f"{re.sub(r'[^0-9]', '', n_m) or n_m} {unit}"
        labels = ["Seg", "Ter", "Qua", "Qui", "Sex"]
        accent_color = "#FACC15"
    elif tid in ("revenue_growth", "money_flow", "bar_chart", "rocket_boost"):
        if "triplic" in low:
            metric = "3X"
            values = [25, 50, 75, 100]
            labels = ["Base", "2x", "Salto", "3X"]
        elif "dobr" in low:
            metric = "2X"
            values = [35, 65, 100]
            labels = ["Antes", "Virada", "2X"]
        elif nums:
            metric = nums[0].upper()
            pct_nums = [n for n in nums if "%" in n]
            parsed_v = []
            for n in nums[:4]:
                d = re.sub(r"[^\d.]", "", n.replace(",", "."))
                try:
                    parsed_v.append(max(5.0, float(d)))
                except Exception:
                    pass
            if pct_nums and tid in ("revenue_growth", "rocket_boost"):
                top_v = float(re.sub(r"[^\d.]", "", pct_nums[0].replace(",", ".")) or 100)
                values = [round(top_v * 0.22, 1), round(top_v * 0.56, 1), round(top_v, 1)]
                labels = ["Início", "Avanço", pct_nums[0][:10]]
            else:
                values = parsed_v if len(parsed_v) >= 3 else ([round(parsed_v[0] * 0.35, 1), round(parsed_v[0] * 0.7, 1), parsed_v[0]] if parsed_v else [30, 62, 95])
                labels = [n[:10] for n in nums[:4]] if len(nums) >= 3 else _clean_clauses(txt, 3, 14)
        else:
            metric = "R$" if tid == "money_flow" else "ALTA"
            labels = _clean_clauses(txt, 3, 14) or merged["labels"]
    elif tid in ("multi_city_map", "route_path"):
        metric = nums[0].upper() if nums else f"{max(2, len(cap_words))} LOCAIS"
        labels = cap_words[:3] if len(cap_words) >= 2 else (_clean_clauses(txt, 3, 14) or merged["labels"])
    elif tid in ("vs_split_card", "before_after_meter"):
        metric = "VS"
        vs_parts = [p.strip(" ,.;:!?") for p in re.split(r"\b(?:vs\.?|contra|mas agora|e agora|enquanto)\b", txt, maxsplit=1, flags=re.I) if p.strip(" ,.;:!?")]
        clauses = vs_parts if len(vs_parts) >= 2 else _clean_clauses(txt, 2, 26)
        labels = ["ANTES", "AGORA"] if ("antes" in low and ("agora" in low or "depois" in low)) else ["LADO A", "LADO B"]
        if len(clauses) >= 2:
            head, accent_text = ("ANTES VS AGORA", "comparação real") if labels[0] == "ANTES" else (clauses[0][:18].upper(), "vs " + clauses[1][:18].lower())
        points = [c[:30] for c in clauses[:2]]
    elif tid in ("donut_share", "counter_kpi"):
        metric = nums[0].upper() if nums else (f"{spoken_num}x" if spoken_num else "FOCO")
        labels = _clean_clauses(txt, 2, 16) or [head]
        if nums:
            try:
                values = [min(100.0, max(10.0, float(re.sub(r"[^\d.]", "", nums[0].replace(",", ".")))))]
            except Exception:
                pass
    else:
        clauses = _clean_clauses(txt, 3, 20)
        labels = clauses if clauses else merged["labels"]
        metric = nums[0].upper() if nums else (head.split()[0][:10] if head else merged["metric"])

    # Theme color harmony
    accent_color = merged["accent_color"]
    if tid == "kinetic_timer" or "minut" in low:
        accent_color = MOOD_PALETTES["gold"]
    elif tid == "sketch_calligraphy" or "imprim" in low:
        accent_color = MOOD_PALETTES["cyan"]
    elif tid in ("money_flow",):
        accent_color = MOOD_PALETTES["gold"]
    elif tid in ("badge_alert",):
        accent_color = MOOD_PALETTES["coral"]

    merged.update({
        "title": head,
        "accent_text": accent_text,
        "subtitle": full_sub[:44],
        "metric": str(metric)[:12],
        "labels": [str(x)[:28] for x in (labels or merged["labels"])[:4]],
        "values": values,
        "points": [str(x)[:38] for x in (points or [full_sub[:38]])[:2]],
        "icon": icon,
        "accent_color": accent_color,
        "position": "bottom-card",
        "visual_prompt": f"Cena '{head} {accent_text}'. {txt[:110]}",
    })
    return {"template_id": tid, "template_name": tpl["name"], "category": tpl["category"], "params": merged}


def build_motion_from_prompt(prompt_text: str, preferred_template_id: str = None) -> dict:
    """Create a custom, script-authentic Motion Graphic scene via Groq LLM + deterministic director."""
    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if groq_key:
        try:
            catalog_summary = [{"id": k, "name": v["name"], "desc": v["description"]} for k, v in MOTION_TEMPLATES.items()]
            pref_note = f"Se fizer sentido visual, use template_id='{preferred_template_id}'." if preferred_template_id in MOTION_TEMPLATES else ""
            sys_prompt = (
                "Você é um Motion Designer sênior para Reels/TikTok.\n"
                "Converta a fala ou prompt em uma cena Motion Graphic CRIATIVA, DINÂMICA e AUTO-EXPLICATIVA que substitui a legenda.\n"
                "REGRAS OBRIGATÓRIAS:\n"
                "1) 'title' DEVE ser uma manchete curta (2-4 palavras) do PRÓPRIO ROTEIRO — NUNCA use o nome genérico do template!\n"
                "2) 'accent_text' deve ter 1-3 palavras em destaque tiradas da fala (ex: 'para imprimir', 'por dia', 'em escala').\n"
                "3) Escolha 'template_id' e 'icon' que realmente combinem com o assunto (ex: papel/caneta para caligrafia, relógio para minutos/rotina, foguete para crescimento).\n"
                "4) NUNCA invente números ou fatos fora do texto.\n"
                "5) Retorne APENAS JSON: "
                "{\"template_id\": string, \"icon\": string, \"title\": string, \"accent_text\": string, \"subtitle\": string, "
                "\"metric\": string, \"labels\": [string], \"values\": [number], \"points\": [string], \"accent_color\": \"#HEX\", \"visual_prompt\": string}.\n"
                f"{pref_note}\nÍcones disponíveis: {list(AVAILABLE_ICONS)}\nTemplates: {json.dumps(catalog_summary, ensure_ascii=False)}\nTexto: {prompt_text}"
            )
            req_body = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": sys_prompt}],
                "temperature": 0.25,
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
            merged["position"] = "bottom-card"
            # Guard against LLM copying template name into title
            llm_title = str(parsed.get("title") or "").strip()
            if not llm_title or llm_title.lower() == tpl["name"].lower():
                llm_title = _extract_script_headline(prompt_text)[0]
            merged["title"] = llm_title[:28]
            for k in ("accent_text", "subtitle", "metric", "visual_prompt"):
                if parsed.get(k):
                    merged[k] = str(parsed[k])[: (42 if k != "visual_prompt" else 140)]
            if parsed.get("icon") in AVAILABLE_ICONS:
                merged["icon"] = parsed["icon"]
            if isinstance(parsed.get("accent_color"), str) and parsed["accent_color"].startswith("#"):
                merged["accent_color"] = parsed["accent_color"][:7]
            if isinstance(parsed.get("labels"), list) and parsed["labels"]:
                merged["labels"] = [str(x)[:18] for x in parsed["labels"][:4]]
            if isinstance(parsed.get("points"), list) and parsed["points"]:
                merged["points"] = [str(x)[:38] for x in parsed["points"][:2]]
            if isinstance(parsed.get("values"), list) and parsed["values"]:
                merged["values"] = [float(x) for x in parsed["values"][:5] if isinstance(x, (int, float))] or merged["values"]
            return {"template_id": tid, "template_name": tpl["name"], "category": tpl["category"], "params": merged}
        except Exception:
            pass
    return _parse_speech_to_scene(prompt_text, preferred_tid=preferred_template_id)


def analyze_video_for_motion(captions, video_path=None):
    """
    Analyze transcript windows and generate bespoke, varied, face-safe Motion Graphics
    whose headlines and visuals directly reflect what is being spoken.
    """
    if not captions:
        return []

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

    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if groq_key:
        try:
            transcript_lines = [f"[{round(w['s'], 2)}s - {round(w['e'], 2)}s] {w['text']}" for w in windows]
            catalog_summary = [{"id": k, "name": v["name"], "desc": v["description"]} for k, v in MOTION_TEMPLATES.items()]
            prompt = (
                "Você é Diretor de Motion Graphics para vídeos curtos (Reels/TikTok).\n"
                "Escolha até 4 trechos da fala para gerar cenas animadas criativas que dão dinamismo e substituem a legenda.\n"
                "REGRAS ESTRITAS:\n"
                "1. 'title' DEVE ser uma manchete curta (2-4 palavras) do ROTEIRO falado — PROIBIDO usar o nome do template!\n"
                "2. Varie os templates e ícones entre sugestões para não repetir estilo visual.\n"
                "3. NUNCA invente números, cidades ou fatos fora da transcrição.\n"
                "4. Retorne APENAS JSON: {\"suggestions\": [{\"start\": number, \"end\": number, \"excerpt\": string, "
                "\"template_id\": string, \"icon\": string, \"title\": string, \"accent_text\": string, \"subtitle\": string, "
                "\"metric\": string, \"labels\": [string], \"values\": [number], \"points\": [string], "
                "\"accent_color\": \"#HEX\", \"reason\": string, \"relevance\": \"Alta\"|\"Média\", \"visual_prompt\": string}]}.\n\n"
                f"ÍCONES: {list(AVAILABLE_ICONS)}\nTEMPLATES:\n{json.dumps(catalog_summary, ensure_ascii=False)}\n\n"
                "TRECHOS:\n" + "\n".join(transcript_lines[:40])
            )
            req_body = json.dumps({
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.25,
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
                e_t = max(s_t + 2.2, min(s_t + 6.2, float(item.get("end", s_t + 3.2))))
                if out and s_t < out[-1]["end"] + 1.5:
                    continue
                merged = dict(tpl["default_params"])
                merged["position"] = "bottom-card"
                ex_txt = str(item.get("excerpt") or "")[:140]
                t_val = str(item.get("title") or "").strip()
                if not t_val or t_val.lower() == tpl["name"].lower():
                    t_val = _extract_script_headline(ex_txt)[0]
                merged["title"] = t_val[:28]
                for k in ("accent_text", "subtitle", "metric", "visual_prompt"):
                    if item.get(k):
                        merged[k] = str(item[k])[: (42 if k != "visual_prompt" else 140)]
                if item.get("icon") in AVAILABLE_ICONS:
                    merged["icon"] = item["icon"]
                if isinstance(item.get("accent_color"), str) and item["accent_color"].startswith("#"):
                    merged["accent_color"] = item["accent_color"][:7]
                if isinstance(item.get("labels"), list) and item["labels"]:
                    merged["labels"] = [str(x)[:18] for x in item["labels"][:4]]
                if isinstance(item.get("points"), list) and item["points"]:
                    merged["points"] = [str(x)[:38] for x in item["points"][:2]]
                if isinstance(item.get("values"), list) and item["values"]:
                    merged["values"] = [float(x) for x in item["values"][:5] if isinstance(x, (int, float))] or merged["values"]
                out.append({
                    "id": f"mg_{idx+1}_{tid}",
                    "start": round(s_t, 2),
                    "end": round(e_t, 2),
                    "excerpt": ex_txt,
                    "subject": merged["title"],
                    "category": tpl["category"],
                    "template_id": tid,
                    "template_name": tpl["name"],
                    "reason": str(item.get("reason") or tpl["description"])[:160],
                    "relevance": "Alta" if str(item.get("relevance", "")).lower().startswith("alt") else "Média",
                    "position": "bottom-card",
                    "replace_captions": True,
                    "prompt": merged.get("visual_prompt", ex_txt),
                    "params": merged,
                    "status": "suggested",
                })
            if out:
                return out
        except Exception:
            pass

    # Deterministic fallback: guarantee script-authentic titles and varied visuals
    suggestions = []
    last_end = -4.0
    used_tids = set()
    for w in windows:
        if suggestions and (w["s"] - last_end < 1.8):
            continue
        txt = w["text"]
        low = txt.lower()
        has_signal = bool(
            re.search(
                r"triplic|dobr|fatur|receit|lucr|dinheir|r\$|%|cidad|estad|pa[ií]s|mapa|rota|trajet|"
                r"antes.*depois|diferen|compar|primeiro|segundo|etapa|passo|processo|fluxo|ciclo|"
                r"\bintelig[eê]ncia\b|\bia\b|sistema|dados|painel|\b(19|20)\d{2}\b|\b\d+\b|"
                r"caligraf|imprim|cole[çc][aã]o|m[eé]todo|aprender|minut|por dia|segredo|motivo|funciona|decol",
                low,
            )
        )
        if not has_signal and len(windows) > 1:
            continue
        scene = _parse_speech_to_scene(txt)
        tid = scene["template_id"]
        if tid in used_tids and len(suggestions) >= 1 and tid == "concept_callout":
            scene = _parse_speech_to_scene(txt, preferred_tid="checklist_reveal")
            tid = scene["template_id"]
        used_tids.add(tid)
        dur = round(min(5.6, max(2.4, w["e"] - w["s"])), 2)
        suggestions.append({
            "id": f"mg_{len(suggestions)+1}_{tid}",
            "start": round(w["s"], 2),
            "end": round(w["s"] + dur, 2),
            "excerpt": txt,
            "subject": scene["params"]["title"],
            "category": scene["category"],
            "template_id": tid,
            "template_name": scene["template_name"],
            "reason": f"Ilustra '{scene['params']['title']}' com {scene['template_name']} no terço inferior sem cobrir o rosto.",
            "relevance": "Alta",
            "position": "bottom-card",
            "replace_captions": True,
            "prompt": scene["params"].get("visual_prompt", txt),
            "params": scene["params"],
            "status": "suggested",
        })
        last_end = w["s"] + dur
        if len(suggestions) >= 4:
            break
    return suggestions


# ---------------------------------------------------------------------------
# 2x Supersampled Vector Primitives, Glass Pills, Glow & Vector Icons
# ---------------------------------------------------------------------------

def _draw_glow_disc(layer: Image.Image, cx: int, cy: int, rx: int, ry: int, rgb: tuple, alpha: int, blur_r: int):
    g = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*rgb, alpha))
    g = g.filter(ImageFilter.GaussianBlur(radius=blur_r))
    layer.alpha_composite(g)


def _draw_glass_pill(draw: ImageDraw.ImageDraw, box, radius: int, accent: tuple, alpha_env: float, tint_rgb=(12, 18, 28), glow_outline: bool = True, bg_alpha: int = 196):
    x0, y0, x1, y1 = [int(v) for v in box]
    bg_a = int(bg_alpha * alpha_env)
    rim_a = int(155 * alpha_env) if glow_outline else int(65 * alpha_env)
    draw.rounded_rectangle([x0 + 3, y0 + 6, x1 + 3, y1 + 8], radius=radius, fill=(0, 0, 0, int(95 * alpha_env)))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=(*tint_rgb, bg_a), outline=(*accent, rim_a), width=2)
    # Specular top glass highlight line
    if x1 - x0 > 40:
        draw.line([(x0 + radius, y0 + 2), (x1 - radius, y0 + 2)], fill=(255, 255, 255, int(68 * alpha_env)), width=2)


def _draw_vector_icon(draw: ImageDraw.ImageDraw, icon_id: str, cx: int, cy: int, sz: int, accent: tuple, alpha_env: float, t_sec: float, anim_p: float):
    fg = (255, 255, 255, int(250 * alpha_env))
    ac = (*accent, int(245 * alpha_env))
    soft = (*accent, int(58 * alpha_env))
    r = max(14, sz // 2)
    pulse = 1.0 + 0.04 * math.sin(t_sec * 4.0)
    rp = int(r * pulse)

    # Outer soft glass medallion around icon
    draw.ellipse([cx - rp, cy - rp, cx + rp, cy + rp], fill=soft, outline=ac, width=3)

    if icon_id == "pen":
        # Stylized nib / fountain pen drawing a curve
        tip_x = cx - int(r * 0.30 + r * 0.45 * anim_p * 0.2)
        tip_y = cy + int(r * 0.30)
        body = [(tip_x, tip_y), (tip_x + int(r * 0.14), tip_y - int(r * 0.34)), (tip_x + int(r * 0.62), tip_y - int(r * 0.80)), (tip_x + int(r * 0.78), tip_y - int(r * 0.64)), (tip_x + int(r * 0.34), tip_y - int(r * 0.14))]
        draw.polygon(body, fill=fg, outline=ac)
        draw.ellipse([tip_x - 5, tip_y - 5, tip_x + 5, tip_y + 5], fill=ac)
    elif icon_id == "clock":
        cr = int(r * 0.56)
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], outline=fg, width=3)
        ang_m = -math.pi / 2 + math.pi * 2 * ((anim_p * 1.4 + t_sec * 0.35) % 1.0)
        draw.line([(cx, cy), (cx + int(cr * 0.65 * math.cos(ang_m)), cy + int(cr * 0.65 * math.sin(ang_m)))], fill=ac, width=4)
        draw.line([(cx, cy), (cx, cy - int(cr * 0.45))], fill=fg, width=4)
        draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=fg)
    elif icon_id == "rocket":
        # Tilted sleek upward rocket
        body = [(cx + int(r * 0.38), cy - int(r * 0.42)), (cx + int(r * 0.12), cy - int(r * 0.02)), (cx - int(r * 0.18), cy + int(r * 0.26)), (cx - int(r * 0.30), cy + int(r * 0.12)), (cx - int(r * 0.02), cy - int(r * 0.18))]
        draw.polygon(body, fill=fg, outline=ac)
        flame = [(cx - int(r * 0.24), cy + int(r * 0.18)), (cx - int(r * 0.52), cy + int(r * 0.46)), (cx - int(r * 0.18), cy + int(r * 0.32))]
        draw.polygon(flame, fill=(250, 204, 21, int(245 * alpha_env)))
    elif icon_id == "coin":
        for k in range(3):
            yy = cy + int(r * 0.26) - k * int(r * 0.22)
            draw.ellipse([cx - int(r * 0.46), yy - int(r * 0.17), cx + int(r * 0.46), yy + int(r * 0.17)], fill=(250, 204, 21, int(245 * alpha_env)), outline=(120, 72, 10, int(230 * alpha_env)), width=2)
    elif icon_id == "check":
        pts = [(cx - int(r * 0.34), cy + int(r * 0.02)), (cx - int(r * 0.08), cy + int(r * 0.30)), (cx + int(r * 0.40), cy - int(r * 0.28))]
        draw.line(pts, fill=fg, width=6, joint="curve")
    elif icon_id == "bolt":
        pts = [(cx + int(r * 0.10), cy - int(r * 0.52)), (cx - int(r * 0.28), cy + int(r * 0.04)), (cx + int(r * 0.04), cy + int(r * 0.04)), (cx - int(r * 0.12), cy + int(r * 0.52)), (cx + int(r * 0.30), cy - int(r * 0.06)), (cx - int(r * 0.02), cy - int(r * 0.06))]
        draw.polygon(pts, fill=fg, outline=ac)
    elif icon_id == "target":
        for f in (0.62, 0.36):
            rr = int(r * f)
            draw.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=fg, width=3)
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=ac)
    elif icon_id == "pin":
        cr = int(r * 0.34)
        draw.polygon([(cx - cr, cy - int(r * 0.08)), (cx + cr, cy - int(r * 0.08)), (cx, cy + int(r * 0.54))], fill=ac)
        draw.ellipse([cx - cr, cy - int(r * 0.44), cx + cr, cy + int(r * 0.20)], fill=fg)
        draw.ellipse([cx - 7, cy - int(r * 0.20), cx + 7, cy - int(r * 0.06)], fill=ac)
    elif icon_id == "chart":
        for bi, bh in enumerate((0.28, 0.48, 0.72)):
            bx = cx - int(r * 0.42) + bi * int(r * 0.32)
            bw = int(r * 0.22)
            by0 = cy + int(r * 0.38) - int(r * bh * anim_p)
            draw.rounded_rectangle([bx, by0, bx + bw, cy + int(r * 0.38)], radius=3, fill=ac if bi == 2 else fg)
    elif icon_id == "book":
        draw.rounded_rectangle([cx - int(r * 0.46), cy - int(r * 0.36), cx + int(r * 0.46), cy + int(r * 0.36)], radius=6, fill=fg, outline=ac, width=2)
        draw.line([(cx, cy - int(r * 0.36)), (cx, cy + int(r * 0.36))], fill=ac, width=3)
    elif icon_id == "trophy":
        draw.polygon([(cx - int(r * 0.36), cy - int(r * 0.36)), (cx + int(r * 0.36), cy - int(r * 0.36)), (cx + int(r * 0.16), cy + int(r * 0.16)), (cx - int(r * 0.16), cy + int(r * 0.16))], fill=(250, 204, 21, int(245 * alpha_env)))
        draw.rectangle([cx - int(r * 0.22), cy + int(r * 0.30), cx + int(r * 0.22), cy + int(r * 0.44)], fill=fg)
        draw.line([(cx, cy + int(r * 0.16)), (cx, cy + int(r * 0.30))], fill=fg, width=5)
    elif icon_id == "bulb":
        cr = int(r * 0.36)
        draw.ellipse([cx - cr, cy - int(r * 0.44), cx + cr, cy + int(r * 0.26)], fill=(250, 204, 21, int(235 * alpha_env)), outline=fg, width=2)
        draw.rounded_rectangle([cx - int(r * 0.18), cy + int(r * 0.24), cx + int(r * 0.18), cy + int(r * 0.44)], radius=4, fill=fg)
    elif icon_id == "flame":
        draw.polygon([(cx, cy - int(r * 0.56)), (cx + int(r * 0.38), cy + int(r * 0.14)), (cx, cy + int(r * 0.48)), (cx - int(r * 0.38), cy + int(r * 0.14))], fill=(251, 146, 60, int(245 * alpha_env)))
        draw.polygon([(cx, cy - int(r * 0.20)), (cx + int(r * 0.18), cy + int(r * 0.18)), (cx, cy + int(r * 0.38)), (cx - int(r * 0.18), cy + int(r * 0.18))], fill=(254, 240, 138, int(245 * alpha_env)))
    else:
        # 4-point kinetic sparkler
        pts = [(cx, cy - int(r * 0.52)), (cx + int(r * 0.15), cy - int(r * 0.15)), (cx + int(r * 0.52), cy), (cx + int(r * 0.15), cy + int(r * 0.15)), (cx, cy + int(r * 0.52)), (cx - int(r * 0.15), cy + int(r * 0.15)), (cx - int(r * 0.52), cy), (cx - int(r * 0.15), cy - int(r * 0.15))]
        draw.polygon(pts, fill=fg, outline=ac)


def _draw_mixed_headline(draw: ImageDraw.ImageDraw, x: int, y: int, title: str, accent_text: str, accent: tuple, alpha_env: float, fonts: dict, align_center: bool = False):
    """Draw editorial mixed typography (ExtraBold sans + BoldItalic serif accent) with crisp shadow."""
    fg_a = int(252 * alpha_env)
    sh_a = int(175 * alpha_env)
    t_str = (title or "")[:28]
    a_str = (accent_text or "")[:24]
    anchor = "mm" if align_center else "lm"

    # Drop shadow then main title
    draw.text((x + 3, y + 4), t_str, font=fonts["title"], fill=(0, 0, 0, sh_a), anchor=anchor)
    draw.text((x, y), t_str, font=fonts["title"], fill=(255, 255, 255, fg_a), anchor=anchor)

    if a_str:
        if align_center:
            draw.text((x + 2, y + 48), a_str, font=fonts["italic"], fill=(0, 0, 0, sh_a), anchor="mm")
            draw.text((x, y + 46), a_str, font=fonts["italic"], fill=(*accent, fg_a), anchor="mm")
        else:
            bbox = draw.textbbox((x, y), t_str, font=fonts["title"], anchor="lm")
            ax = bbox[2] + 14
            if ax > 1060:  # wrap cleanly below if long
                draw.text((x + 2, y + 48), a_str, font=fonts["italic"], fill=(0, 0, 0, sh_a), anchor="lm")
                draw.text((x, y + 46), a_str, font=fonts["italic"], fill=(*accent, fg_a), anchor="lm")
            else:
                draw.text((ax + 2, y + 3), a_str, font=fonts["italic"], fill=(0, 0, 0, sh_a), anchor="lm")
                draw.text((ax, y + 1), a_str, font=fonts["italic"], fill=(*accent, fg_a), anchor="lm")


def _draw_motion_frame(tpl_id: str, params: dict, prog: float, t_sec: float, w: int, h: int, fonts: dict) -> Image.Image:
    """Render one 2x supersampled transparent RGBA frame, downscaled cleanly via LANCZOS."""
    W2, H2 = w * 2, h * 2
    img = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    accent = _hex_to_rgb(params.get("accent_color") or "#22C55E")
    easing_mode = params.get("easing") or "spring"
    enter_p = _ease(min(1.0, prog / 0.18), easing_mode)
    exit_p = _ease(min(1.0, (1.0 - prog) / 0.14), "smooth")
    alpha_env = max(0.0, min(1.0, min(enter_p, exit_p)))
    anim_p = _ease(max(0.0, min(1.0, (prog - 0.04) / 0.68)), easing_mode)
    float_dy = int(math.sin(t_sec * 2.6) * 8)

    title = str(params.get("title") or "").strip()
    if not title:
        title = _extract_script_headline(str(params.get("subtitle") or "Destaque"))[0]
    accent_text = str(params.get("accent_text") or "").strip()
    subtitle = str(params.get("subtitle") or "")[:44]
    metric = str(params.get("metric") or "")[:12]
    icon_id = str(params.get("icon") or _pick_icon_from_text(f"{title} {subtitle}".lower(), tpl_id))
    labels = [str(x)[:28] for x in (params.get("labels") or ["Item 1", "Item 2", "Item 3"])]
    points = [str(x)[:40] for x in (params.get("points") or ([subtitle] if subtitle else []))]
    vals = [float(v) for v in (params.get("values") or [30, 68, 98]) if isinstance(v, (int, float))] or [35, 70, 100]

    # Ambient radial soft dark cushion behind center-bottom text zone so text is 100% readable without boxy border!
    slide_y = int((1.0 - enter_p) * 54) + float_dy
    _draw_glow_disc(img, W2 // 2, H2 // 2 + slide_y // 2, int(W2 * 0.42), int(H2 * 0.36), (6, 10, 16), int(165 * alpha_env), blur_r=48)
    _draw_glow_disc(img, int(W2 * 0.25), int(H2 * 0.48) + slide_y // 2, int(W2 * 0.20), int(H2 * 0.20), accent, int(68 * alpha_env), blur_r=52)
    draw = ImageDraw.Draw(img, "RGBA")

    # Floating ambient kinetic motes
    for m_i in range(6):
        mx = int(W2 * (0.10 + 0.16 * m_i) + 18 * math.sin(t_sec * 1.4 + m_i))
        my = int(H2 * (0.20 + 0.55 * ((m_i * 0.37 + t_sec * 0.12) % 1.0)))
        draw.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=(*accent, int(130 * alpha_env)))

    fg_a = int(252 * alpha_env)
    sx, sy = 76, 54 + slide_y

    # ---- SCENE 1: SKETCH & CALLIGRAPHY (Floating page + live cursive pen drawing!) ----
    if tpl_id == "sketch_calligraphy":
        # Crisp cream notepad sheet floating on left
        px0, py0, px1, py1 = 68, 72 + slide_y, 500, H2 - 70 + slide_y
        _draw_glass_pill(draw, [px0, py0, px1, py1], 28, accent, alpha_env, tint_rgb=(252, 250, 244), glow_outline=True, bg_alpha=242)
        # Ruled calligraphy guide lines on sheet
        for ln in range(4):
            ly = py0 + 76 + ln * 56
            draw.line([(px0 + 36, ly), (px1 - 36, ly)], fill=(140, 165, 195, int(135 * alpha_env)), width=2)
        # Animated continuous cursive calligraphic wave drawn dynamically with pen tip!
        curve_pts = []
        steps = 44
        draw_cnt = max(2, int(steps * anim_p))
        for si in range(draw_cnt):
            u = si / float(steps - 1)
            cx_w = px0 + 48 + int((px1 - px0 - 96) * u)
            cy_w = py0 + 186 - int(58 * math.sin(u * math.pi * 3.0) * math.exp(-0.2 * u) + 18 * math.cos(u * math.pi * 6.0))
            curve_pts.append((cx_w, cy_w))
        if len(curve_pts) >= 2:
            draw.line(curve_pts, fill=(*accent, fg_a), width=10, joint="curve")
            tx, ty = curve_pts[-1]
            # Moving pen nib right on the active ink tip!
            draw.polygon([(tx, ty), (tx + 18, ty - 42), (tx + 68, ty - 96), (tx + 84, ty - 80), (tx + 34, ty - 24)], fill=(20, 28, 42, fg_a), outline=(*accent, fg_a))
            draw.ellipse([tx - 8, ty - 8, tx + 8, ty + 8], fill=(255, 255, 255, fg_a))

        # Right side kinetic script headline & floating pill tags
        rx = 560
        _draw_mixed_headline(draw, rx, 130 + slide_y, title, accent_text, accent, alpha_env, fonts)
        for ci, lbl in enumerate(labels[:3]):
            cx_p = rx + ci * 188
            cy_p = 240 + slide_y
            shown = anim_p >= ci * 0.22
            if shown:
                _draw_glass_pill(draw, [cx_p, cy_p, cx_p + 170, cy_p + 66], 33, accent, alpha_env)
                draw.text((cx_p + 85, cy_p + 33), lbl[:12], font=fonts["pill"], fill=(255, 255, 255, fg_a), anchor="mm")
        if points:
            _draw_glass_pill(draw, [rx, 344 + slide_y, W2 - 70, 426 + slide_y], 24, accent, alpha_env, glow_outline=False)
            draw.text((rx + 28, 385 + slide_y), points[0][:38], font=fonts["sub"], fill=(235, 245, 255, fg_a), anchor="lm")

    # ---- SCENE 2: KINETIC TIMER & HABIT STREAK ----
    elif tpl_id == "kinetic_timer":
        cx, cy, rad = 250, H2 // 2 + slide_y, 148
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(12, 18, 28, int(195 * alpha_env)), outline=(255, 255, 255, int(45 * alpha_env)), width=4)
        draw.arc([cx - rad + 18, cy - rad + 18, cx + rad - 18, cy + rad - 18], start=-90, end=-90 + int(360 * anim_p), fill=(*accent, fg_a), width=18)
        draw.text((cx, cy - 10), metric[:9], font=fonts["hero_md"], fill=(255, 255, 255, fg_a), anchor="mm")
        draw.text((cx, cy + 44), (accent_text or "POR DIA")[:14].upper(), font=fonts["sub"], fill=(*accent, fg_a), anchor="mm")

        rx = 460
        _draw_mixed_headline(draw, rx, 130 + slide_y, title, accent_text, accent, alpha_env, fonts)
        for si, day_lbl in enumerate(labels[:5]):
            lit = anim_p >= (si / 5.0)
            px = rx + si * 116
            py = 240 + slide_y
            _draw_glass_pill(draw, [px, py, px + 100, py + 74], 24, accent if lit else (148, 163, 184), alpha_env, tint_rgb=accent if lit else (16, 22, 34), glow_outline=lit)
            tcol = (12, 16, 22, fg_a) if lit else (220, 230, 240, fg_a)
            draw.text((px + 50, py + 37), day_lbl[:6], font=fonts["pill"], fill=tcol, anchor="mm")
        if points:
            draw.text((rx, 374 + slide_y), points[0][:40], font=fonts["sub"], fill=(235, 244, 255, fg_a), anchor="lm")

    # ---- SCENE 3: KINETIC CURVE (Frameless glowing spline + transparent bottom fade!) ----
    elif tpl_id == "revenue_growth":
        _draw_mixed_headline(draw, 84, 78 + slide_y, title, accent_text, accent, alpha_env, fonts)
        if metric:
            _draw_glass_pill(draw, [W2 - 330, 46 + slide_y, W2 - 76, 124 + slide_y], 39, accent, alpha_env)
            draw.text((W2 - 203, 85 + slide_y), metric, font=fonts["metric"], fill=(*accent, fg_a), anchor="mm")

        gx0, gy0, gx1, gy1 = 110, 190 + slide_y, W2 - 110, H2 - 135 + slide_y
        cvals = list(vals[:4])
        while len(cvals) < 3:
            cvals.insert(0, max(5.0, round(cvals[0] * 0.45, 1)))
        n_p = len(cvals)
        vmax = max(cvals) or 100.0
        pts = [(gx0 + int(((gx1 - gx0) * i) / (n_p - 1)), gy1 - int((gy1 - gy0) * 0.88 * (cvals[i] / vmax) * anim_p)) for i in range(n_p)]
        # Layered soft area fill bands fading downward
        for band, b_al in ((1.0, 56), (0.66, 36), (0.33, 16)):
            bpts = [(px, int(gy1 - (gy1 - py) * band)) for px, py in pts] + [(pts[-1][0], gy1), (pts[0][0], gy1)]
            draw.polygon(bpts, fill=(*accent, int(b_al * alpha_env)))
        draw.line(pts, fill=(*accent, fg_a), width=10, joint="curve")
        for i, (px, py) in enumerate(pts):
            if anim_p >= i / float(n_p):
                draw.line([(px, py), (px, gy1)], fill=(*accent, int(90 * alpha_env)), width=3)
                draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=(255, 255, 255, fg_a), outline=(*accent, fg_a), width=5)
                if i < len(labels):
                    _draw_glass_pill(draw, [px - 88, py - 68, px + 88, py - 24], 20, accent, alpha_env)
                    draw.text((px, py - 46), labels[i][:12], font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")
        if points:
            pw_b = min(W2 - 180, len(points[0]) * 21 + 64)
            _draw_glass_pill(draw, [W2 // 2 - pw_b // 2, H2 - 84 + slide_y, W2 // 2 + pw_b // 2, H2 - 32 + slide_y], 24, accent, alpha_env, glow_outline=False)
            draw.text((W2 // 2, H2 - 58 + slide_y), points[0][:44], font=fonts["sub"], fill=(248, 252, 250, fg_a), anchor="mm")

    # ---- SCENE 4: ROCKET BOOST (Shaded launch path + flame + metric pill) ----
    elif tpl_id == "rocket_boost":
        # Ascending trajectory arc from bottom-left to top-center
        arc_pts = []
        steps = 28
        for si in range(max(2, int(steps * anim_p))):
            u = si / float(steps - 1)
            ax = 120 + int(420 * u)
            ay = H2 - 90 + slide_y - int(290 * (u ** 1.35))
            arc_pts.append((ax, ay))
        if len(arc_pts) >= 2:
            draw.line(arc_pts, fill=(*accent, int(220 * alpha_env)), width=12, joint="curve")
            rx_r, ry_r = arc_pts[-1]
            _draw_vector_icon(draw, "rocket", rx_r, ry_r, 118, accent, alpha_env, t_sec, anim_p)
        tx = 590
        _draw_mixed_headline(draw, tx, 108 + slide_y, title, accent_text, accent, alpha_env, fonts)
        _draw_glass_pill(draw, [tx, 238 + slide_y, tx + 290, 340 + slide_y], 32, accent, alpha_env)
        draw.text((tx + 145, 289 + slide_y), metric or "DECOLAGEM", font=fonts["hero_md"], fill=(*accent, fg_a), anchor="mm")
        if points:
            _draw_glass_pill(draw, [tx, 366 + slide_y, W2 - 70, 424 + slide_y], 20, accent, alpha_env, glow_outline=False)
            draw.text((tx + 22, 395 + slide_y), points[0][:38], font=fonts["sub"], fill=(240, 250, 245, fg_a), anchor="lm")

    # ---- SCENE 5: MONEY FLOW (Spring-bouncing 3D coins + glass vault pill) ----
    elif tpl_id == "money_flow":
        _draw_mixed_headline(draw, 84, 78 + slide_y, title, accent_text, accent, alpha_env, fonts)
        for col_i in range(3):
            cx = 140 + col_i * 126
            coins = max(2, int((2 + col_i * 2) * anim_p) + 1)
            for ci in range(coins):
                cy = H2 - 110 + slide_y - ci * 32
                draw.ellipse([cx - 48, cy - 18, cx + 48, cy + 18], fill=(250, 204, 21, fg_a), outline=(120, 72, 12, fg_a), width=3)
                draw.text((cx, cy), "$", font=fonts["pill"], fill=(42, 24, 4, fg_a), anchor="mm")
        vx0, vy0, vx1, vy1 = 560, 175 + slide_y, W2 - 80, H2 - 90 + slide_y
        _draw_glass_pill(draw, [vx0, vy0, vx1, vy1], 36, accent, alpha_env)
        draw.text(((vx0 + vx1) // 2, (vy0 + vy1) // 2 - 22), metric or "R$", font=fonts["hero"], fill=(250, 204, 21, fg_a), anchor="mm")
        if points:
            draw.text(((vx0 + vx1) // 2, (vy0 + vy1) // 2 + 64), points[0][:34], font=fonts["sub"], fill=(255, 252, 235, fg_a), anchor="mm")

    # ---- SCENE 6: DUAL FLOATING GLASS CARDS (Manual vs Automático / Antes vs Agora) ----
    elif tpl_id in ("vs_split_card", "before_after_meter"):
        _draw_mixed_headline(draw, W2 // 2, 68 + slide_y, title, accent_text, accent, alpha_env, fonts, align_center=True)
        slide_lr = int((1.0 - enter_p) * 140)
        mid = W2 // 2
        # Left card sliding from left
        _draw_glass_pill(draw, [76 - slide_lr, 165 + slide_y, mid - 58 - slide_lr, H2 - 85 + slide_y], 34, (244, 63, 94), alpha_env, tint_rgb=(42, 16, 24))
        draw.text(((76 + mid - 58) // 2 - slide_lr, 238 + slide_y), labels[0][:16], font=fonts["title_sm"], fill=(254, 205, 211, fg_a), anchor="mm")
        if points:
            draw.text(((76 + mid - 58) // 2 - slide_lr, 312 + slide_y), points[0][:28], font=fonts["sub"], fill=(255, 240, 244, fg_a), anchor="mm")

        # Right card sliding from right
        r_lbl = labels[1] if len(labels) > 1 else "Depois"
        _draw_glass_pill(draw, [mid + 58 + slide_lr, 165 + slide_y, W2 - 76 + slide_lr, H2 - 85 + slide_y], 34, accent, alpha_env, tint_rgb=(12, 36, 24))
        draw.text(((mid + 58 + W2 - 76) // 2 + slide_lr, 238 + slide_y), r_lbl[:16], font=fonts["title_sm"], fill=(187, 247, 208, fg_a), anchor="mm")
        if len(points) > 1:
            draw.text(((mid + 58 + W2 - 76) // 2 + slide_lr, 312 + slide_y), points[1][:28], font=fonts["sub"], fill=(235, 255, 245, fg_a), anchor="mm")

        # Center lightning badge
        _draw_vector_icon(draw, "bolt", mid, 305 + slide_y, 102, accent, alpha_env, t_sec, anim_p)

    # ---- SCENE 7: RADAR GLOBE & FLIGHT ARCS (Mapas / Rotas) ----
    elif tpl_id in ("multi_city_map", "route_path"):
        _draw_mixed_headline(draw, 84, 72 + slide_y, title, accent_text, accent, alpha_env, fonts)
        cx_g, cy_g = W2 // 2, 300 + slide_y
        # Translucent curved globe rings
        for rr in (180, 320, 460):
            draw.ellipse([cx_g - rr, cy_g - int(rr * 0.42), cx_g + rr, cy_g + int(rr * 0.42)], outline=(148, 197, 255, int(65 * alpha_env)), width=2)
        n_pins = max(2, min(3, len(labels)))
        pin_pts = [(230 + int((W2 - 460) * i / float(max(1, n_pins - 1))), 345 + slide_y if i % 2 == 0 else 235 + slide_y) for i in range(n_pins)]
        for i in range(len(pin_pts) - 1):
            p0, p1 = pin_pts[i], pin_pts[i + 1]
            apts = []
            for st in range(max(2, int(24 * anim_p))):
                u = st / 23.0
                apts.append((int(p0[0] + (p1[0] - p0[0]) * u), int(p0[1] + (p1[1] - p0[1]) * u - 88 * math.sin(math.pi * u))))
            if len(apts) >= 2:
                draw.line(apts, fill=(*accent, fg_a), width=8)
                draw.ellipse([apts[-1][0] - 11, apts[-1][1] - 11, apts[-1][0] + 11, apts[-1][1] + 11], fill=(255, 255, 255, fg_a))
        for i, (px, py) in enumerate(pin_pts):
            pulse = 22 + int(12 * abs(math.sin(t_sec * 4.0 + i)))
            draw.ellipse([px - pulse, py - pulse, px + pulse, py + pulse], outline=(*accent, int(145 * alpha_env)), width=3)
            draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=(*accent, fg_a), outline=(255, 255, 255, fg_a), width=3)
            _draw_glass_pill(draw, [px - 115, py + 24, px + 115, py + 80], 26, accent, alpha_env)
            draw.text((px, py + 52), labels[i][:15], font=fonts["pill"], fill=(255, 255, 255, fg_a), anchor="mm")

    # ---- SCENE 8: CHECKLIST REVEAL (Animated vector checkmarks + points) ----
    elif tpl_id == "checklist_reveal":
        _draw_mixed_headline(draw, 88, 78 + slide_y, title, accent_text, accent, alpha_env, fonts)
        items = labels[:3] if len(labels) >= 2 else (points or ["Item 1", "Item 2"])
        for i, it_txt in enumerate(items[:3]):
            lit = anim_p >= i * 0.28
            iy = 165 + i * 102 + slide_y
            if lit:
                _draw_glass_pill(draw, [88, iy, W2 - 88, iy + 84], 28, accent, alpha_env)
                _draw_vector_icon(draw, "check", 142, iy + 42, 56, accent, alpha_env, t_sec, anim_p)
                draw.text((206, iy + 42), it_txt[:34], font=fonts["title_sm"], fill=(255, 255, 255, fg_a), anchor="lm")

    # ---- SCENE 9: BAR CHART (Frameless glass columns + value tags) ----
    elif tpl_id == "bar_chart":
        _draw_mixed_headline(draw, 84, 72 + slide_y, title, accent_text, accent, alpha_env, fonts)
        bvals = list(vals[:4])
        while len(bvals) < 2:
            bvals.insert(0, max(5.0, round(bvals[0] * 0.5, 1)))
        nb = len(bvals)
        vmax = max(bvals) or 100.0
        gx0, gy1 = 140, H2 - 96 + slide_y
        gw = W2 - 280
        gap = 42
        bw_c = max(72, (gw - gap * (nb - 1)) // nb)
        for i in range(nb):
            sp = _ease(min(1.0, max(0.0, (anim_p - i * 0.10) / 0.65)), easing_mode)
            ch = max(24, int(235 * (bvals[i] / vmax) * sp))
            bx_c = gx0 + i * (bw_c + gap)
            by_top = gy1 - ch
            is_last = (i == nb - 1)
            col = (*accent, fg_a) if is_last else (148, 197, 240, int(175 * alpha_env))
            draw.rounded_rectangle([bx_c, by_top, bx_c + bw_c, gy1], radius=20, fill=col)
            draw.text((bx_c + bw_c // 2, by_top - 22), str(int(bvals[i] * sp)), font=fonts["pill"], fill=(255, 255, 255, fg_a), anchor="mb")
            lbl = labels[i] if i < len(labels) else f"#{i+1}"
            draw.text((bx_c + bw_c // 2, gy1 + 26), lbl[:12], font=fonts["sub"], fill=(225, 240, 255, fg_a), anchor="mm")

    # ---- SCENE 10: DONUT SHARE / RADIALL GAUGE ----
    elif tpl_id == "donut_share":
        cx, cy, rad = 240, H2 // 2 + slide_y, 140
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(255, 255, 255, int(42 * alpha_env)), width=28)
        sw = int((vals[0] / 100.0 if vals[0] <= 100 else 0.80) * 360 * anim_p)
        draw.arc([cx - rad, cy - rad, cx + rad, cy + rad], start=-90, end=-90 + sw, fill=(*accent, fg_a), width=28)
        draw.text((cx, cy), metric[:8], font=fonts["hero_md"], fill=(255, 255, 255, fg_a), anchor="mm")
        rx = 445
        _draw_mixed_headline(draw, rx, 115 + slide_y, title, accent_text, accent, alpha_env, fonts)
        for i, lbl in enumerate(labels[:3]):
            ry = 205 + i * 84 + slide_y
            pct = min(100.0, vals[i] if i < len(vals) else max(25.0, 82.0 - i * 25.0))
            draw.text((rx, ry), lbl[:20], font=fonts["pill"], fill=(255, 255, 255, fg_a), anchor="lm")
            draw.rounded_rectangle([rx, ry + 24, W2 - 80, ry + 44], radius=10, fill=(255, 255, 255, int(35 * alpha_env)))
            draw.rounded_rectangle([rx, ry + 24, rx + max(24, int((W2 - 80 - rx) * (pct / 100.0) * anim_p)), ry + 44], radius=10, fill=(*accent, fg_a))

    # ---- SCENE 11: FLOW STEPS / TIMELINE / CYCLE ----
    elif tpl_id in ("flow_diagram", "timeline_steps", "cycle_loop"):
        _draw_mixed_headline(draw, 84, 72 + slide_y, title, accent_text, accent, alpha_env, fonts)
        n_st = max(2, min(3, len(labels)))
        gap = 56
        sw = (W2 - 168 - gap * (n_st - 1)) // n_st
        cy = 290 + slide_y
        # Connecting laser line with traveling energy orb
        if n_st >= 2:
            x_a, x_b = 84 + sw // 2, 84 + (n_st - 1) * (sw + gap) + sw // 2
            draw.line([(x_a, cy), (x_b, cy)], fill=(255, 255, 255, int(45 * alpha_env)), width=8)
            x_act = x_a + int((x_b - x_a) * anim_p)
            draw.line([(x_a, cy), (x_act, cy)], fill=(*accent, fg_a), width=8)
            draw.ellipse([x_act - 12, cy - 12, x_act + 12, cy + 12], fill=(255, 255, 255, fg_a))
        for i in range(n_st):
            lit = anim_p >= i / float(n_st)
            bx_s = 84 + i * (sw + gap)
            _draw_glass_pill(draw, [bx_s, cy - 68, bx_s + sw, cy + 72], 28, accent if lit else (148, 163, 184), alpha_env, glow_outline=lit)
            draw.ellipse([bx_s + sw // 2 - 26, cy - 94, bx_s + sw // 2 + 26, cy - 42], fill=(*accent, fg_a if lit else int(120 * alpha_env)))
            draw.text((bx_s + sw // 2, cy - 68), f"0{i+1}", font=fonts["pill"], fill=(12, 16, 22, fg_a), anchor="mm")
            draw.text((bx_s + sw // 2, cy + 14), (labels[i] if i < len(labels) else f"Etapa {i+1}")[:15], font=fonts["title_sm"], fill=(255, 255, 255, fg_a), anchor="mm")
        if points:
            draw.text((W2 // 2, H2 - 58 + slide_y), points[0][:44], font=fonts["sub"], fill=(235, 245, 245, fg_a), anchor="mm")

    # ---- SCENE 12: COUNTER KPI ----
    elif tpl_id == "counter_kpi":
        _draw_mixed_headline(draw, W2 // 2, 82 + slide_y, title, accent_text, accent, alpha_env, fonts, align_center=True)
        m_num = re.findall(r"\d+", metric)
        center_txt = metric
        if m_num:
            center_txt = metric.replace(m_num[0], str(int(int(m_num[0]) * anim_p)), 1)
        _draw_glass_pill(draw, [W2 // 2 - 260, 175 + slide_y, W2 // 2 + 260, 355 + slide_y], 42, accent, alpha_env)
        draw.text((W2 // 2, 265 + slide_y), center_txt[:12], font=fonts["hero"], fill=(*accent, fg_a), anchor="mm")
        if points:
            draw.text((W2 // 2, H2 - 64 + slide_y), points[0][:42], font=fonts["sub"], fill=(245, 250, 255, fg_a), anchor="mm")

    # ---- SCENE 13: AI NETWORK / TECH HUD / HERO ICON CONCEPT SPOTLIGHT ----
    else:
        # Frameless Hero Vector Illustration on left + Mixed Editorial Typography + Highlight Sweep + Chips!
        _draw_vector_icon(draw, icon_id, 220, H2 // 2 + slide_y, 210, accent, alpha_env, t_sec, anim_p)
        rx = 390
        _draw_mixed_headline(draw, rx, 130 + slide_y, title, accent_text, accent, alpha_env, fonts)
        # Animated highlight pill bar behind takeaway
        if points:
            hl_w = max(80, int((W2 - rx - 80) * anim_p))
            _draw_glass_pill(draw, [rx, 212 + slide_y, rx + hl_w, 294 + slide_y], 26, accent, alpha_env)
            if anim_p > 0.35:
                draw.text((rx + 28, 253 + slide_y), points[0][:38], font=fonts["title_sm"], fill=(255, 255, 255, fg_a), anchor="lm")
        for ci, lbl in enumerate(labels[:3]):
            cx_p = rx + ci * 195
            cy_p = 326 + slide_y
            if cx_p + 175 <= W2 - 40 and anim_p >= ci * 0.18:
                _draw_glass_pill(draw, [cx_p, cy_p, cx_p + 176, cy_p + 58], 28, accent, alpha_env, glow_outline=False)
                draw.text((cx_p + 88, cy_p + 29), lbl[:12], font=fonts["pill"], fill=(240, 248, 255, fg_a), anchor="mm")

    return img.resize((w, h), Image.LANCZOS)


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
    """Render 2x supersampled frameless Motion Graphic into transparent RGBA .mov overlay clip."""
    from processor import find_ffmpeg

    ffmpeg, _ = find_ffmpeg()
    tpl = MOTION_TEMPLATES.get(template_id, MOTION_TEMPLATES["concept_callout"])
    merged = dict(tpl["default_params"])
    merged.update(params or {})

    dur = max(1.2, min(10.0, float(duration or 3.2)))
    speed = max(0.5, min(2.0, float(merged.get("speed", 1.0))))
    w = max(320, int(width) - (int(width) % 2))
    h = max(200, int(height) - (int(height) % 2))
    total_frames = max(12, int(round(dur * fps)))

    # 2x font sizes because _draw_motion_frame draws on W2=2*w, H2=2*h
    sc = (w * 2) / 1720.0
    fonts = {
        "title": _load_font("CreatoDisplay-ExtraBold.otf", int(62 * sc)),
        "title_sm": _load_font("CreatoDisplay-Bold.otf", int(42 * sc)),
        "italic": _load_font("AppleGaramond-BoldItalic.ttf", int(64 * sc)),
        "pill": _load_font("CreatoDisplay-Bold.otf", int(32 * sc)),
        "sub": _load_font("DMSans.ttf", int(34 * sc)),
        "metric": _load_font("CreatoDisplay-ExtraBold.otf", int(50 * sc)),
        "hero_md": _load_font("CreatoDisplay-ExtraBold.otf", int(76 * sc)),
        "hero": _load_font("BebasNeue-Regular.ttf", int(134 * sc)),
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
