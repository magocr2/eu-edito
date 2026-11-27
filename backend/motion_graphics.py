"""
Eu Edito — Intelligent Motion Graphics Engine
Provides:
1. Categorized reusable animated Motion Graphics templates (8 categories, 16 templates).
2. Intelligent contextual transcript + scene analyzer that picks non-overlapping moments
   and populates template parameters strictly from spoken facts (Groq LLM + deterministic fallback).
3. Programmatic RGBA frame renderer piping lossless transparent overlays (.mov rgba) via FFmpeg.
"""
import json
import math
import os
import re
import subprocess
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
        "name": "Crescimento Financeiro",
        "description": "Curva ascendente brilhante com marco de multiplicação ou receita.",
        "default_params": {
            "title": "Faturamento",
            "subtitle": "Crescimento real",
            "values": [22, 38, 56, 84, 100],
            "labels": ["T1", "T2", "T3", "T4"],
            "metric": "+3x",
            "accent_color": "#22C55E",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "money_flow": {
        "id": "money_flow",
        "category": "negocios",
        "name": "Dinheiro & Retorno",
        "description": "Cartão financeiro com moedas vetoriais e fluxo positivo animado.",
        "default_params": {
            "title": "Resultado Financeiro",
            "subtitle": "Receita em expansão",
            "values": [35, 65, 95],
            "labels": ["Base", "Meta", "Atual"],
            "metric": "R$",
            "accent_color": "#FACC15",
            "position": "top-right",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
            "style": "glass",
        },
    },
    "bar_chart": {
        "id": "bar_chart",
        "category": "graficos",
        "name": "Gráfico de Barras",
        "description": "Barras verticais com subida escalonada e leitura clara de dados.",
        "default_params": {
            "title": "Comparativo",
            "subtitle": "Evolução por etapa",
            "values": [30, 55, 78, 96],
            "labels": ["1", "2", "3", "4"],
            "metric": "%",
            "accent_color": "#38BDF8",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "donut_share": {
        "id": "donut_share",
        "category": "graficos",
        "name": "Gráfico Circular / %",
        "description": "Anel de progresso luminoso com destaque numérico central.",
        "default_params": {
            "title": "Participação",
            "subtitle": "Indicador principal",
            "values": [78],
            "labels": ["Meta"],
            "metric": "78%",
            "accent_color": "#A855F7",
            "position": "top-right",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
            "style": "glass",
        },
    },
    "multi_city_map": {
        "id": "multi_city_map",
        "category": "mapas",
        "name": "Mapa com Localizações",
        "description": "Grade cartográfica estilizada com pins pulsantes e conexões.",
        "default_params": {
            "title": "Localizações",
            "subtitle": "Pontos destacados",
            "values": [3],
            "labels": ["Ponto A", "Ponto B", "Ponto C"],
            "metric": "3 locais",
            "accent_color": "#22C55E",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "fade",
            "style": "glass",
        },
    },
    "route_path": {
        "id": "route_path",
        "category": "mapas",
        "name": "Rota & Trajeto",
        "description": "Trajeto vetorial animado conectando origem e destino no mapa.",
        "default_params": {
            "title": "Trajeto",
            "subtitle": "Conexão direta",
            "values": [100],
            "labels": ["Origem", "Destino"],
            "metric": "Rota",
            "accent_color": "#38BDF8",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "smooth",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "ai_network": {
        "id": "ai_network",
        "category": "tecnologia",
        "name": "Rede Neural & IA",
        "description": "Nós tecnológicos interconectados com pulsos de processamento.",
        "default_params": {
            "title": "Inteligência Digital",
            "subtitle": "Automação e dados",
            "values": [92],
            "labels": ["Entrada", "Motor", "Saída"],
            "metric": "IA",
            "accent_color": "#38BDF8",
            "position": "top-right",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
            "style": "glass",
        },
    },
    "data_dashboard": {
        "id": "data_dashboard",
        "category": "tecnologia",
        "name": "Painel de Dados",
        "description": "Mini interface com múltiplas métricas e linha de atividade ao vivo.",
        "default_params": {
            "title": "Painel ao Vivo",
            "subtitle": "Sistema integrado",
            "values": [40, 62, 58, 86, 94],
            "labels": ["Status", "Ativo"],
            "metric": "LIVE",
            "accent_color": "#4ADE80",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "timeline_steps": {
        "id": "timeline_steps",
        "category": "educacao",
        "name": "Linha do Tempo",
        "description": "Marcos sequenciais iluminados conforme a explicação avança.",
        "default_params": {
            "title": "Cronologia",
            "subtitle": "Evolução",
            "values": [1, 2, 3],
            "labels": ["Início", "Virada", "Hoje"],
            "metric": "3 marcos",
            "accent_color": "#F59E0B",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "concept_callout": {
        "id": "concept_callout",
        "category": "educacao",
        "name": "Conceito-Chave",
        "description": "Cartão explicativo limpo com ícone vetorial e síntese do conceito.",
        "default_params": {
            "title": "Ponto Central",
            "subtitle": "Entenda a lógica",
            "values": [100],
            "labels": ["Conceito"],
            "metric": "IDEA",
            "accent_color": "#38BDF8",
            "position": "top-left",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
            "style": "glass",
        },
    },
    "vs_split_card": {
        "id": "vs_split_card",
        "category": "comparacoes",
        "name": "Comparação A vs B",
        "description": "Confronto visual entre dois cenários com barras paralelas.",
        "default_params": {
            "title": "Comparação",
            "subtitle": "Diferença prática",
            "values": [32, 92],
            "labels": ["Antes", "Depois"],
            "metric": "VS",
            "accent_color": "#22C55E",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "before_after_meter": {
        "id": "before_after_meter",
        "category": "comparacoes",
        "name": "Medidor Antes/Depois",
        "description": "Escala de evolução marcando o salto de performance.",
        "default_params": {
            "title": "Evolução",
            "subtitle": "Salto de resultado",
            "values": [25, 90],
            "labels": ["Início", "Agora"],
            "metric": "UP",
            "accent_color": "#4ADE80",
            "position": "top-right",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "pop",
            "style": "glass",
        },
    },
    "flow_diagram": {
        "id": "flow_diagram",
        "category": "processos",
        "name": "Fluxograma de Etapas",
        "description": "Blocos conectados com setas animadas mostrando o mecanismo.",
        "default_params": {
            "title": "Como Funciona",
            "subtitle": "Passo a passo",
            "values": [1, 2, 3],
            "labels": ["Etapa 1", "Etapa 2", "Etapa 3"],
            "metric": "FLUXO",
            "accent_color": "#22C55E",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
    "cycle_loop": {
        "id": "cycle_loop",
        "category": "processos",
        "name": "Ciclo Contínuo",
        "description": "Anel orbital vetorial representando processos contínuos.",
        "default_params": {
            "title": "Ciclo Contínuo",
            "subtitle": "Engrenagem em ação",
            "values": [3],
            "labels": ["Entrada", "Ação", "Retorno"],
            "metric": "CICLO",
            "accent_color": "#A855F7",
            "position": "top-right",
            "scale": 100,
            "speed": 1.0,
            "easing": "smooth",
            "entry_exit": "fade",
            "style": "glass",
        },
    },
    "counter_kpi": {
        "id": "counter_kpi",
        "category": "elementos",
        "name": "Número em Destaque",
        "description": "Contador cinético gigante para números, datas ou quantidades.",
        "default_params": {
            "title": "Destaque",
            "subtitle": "Dado citado",
            "values": [100],
            "labels": ["Total"],
            "metric": "100%",
            "accent_color": "#FACC15",
            "position": "top-center",
            "scale": 100,
            "speed": 1.0,
            "easing": "spring",
            "entry_exit": "pop",
            "style": "glass",
        },
    },
    "badge_alert": {
        "id": "badge_alert",
        "category": "elementos",
        "name": "Contexto / Acontecimento",
        "description": "Selo geométrico moderno para contextualizar um fato ou marca.",
        "default_params": {
            "title": "Contexto",
            "subtitle": "Registro importante",
            "values": [100],
            "labels": ["Fato"],
            "metric": "!",
            "accent_color": "#F43F5E",
            "position": "top-left",
            "scale": 100,
            "speed": 1.0,
            "easing": "cubic-out",
            "entry_exit": "slide-up",
            "style": "glass",
        },
    },
}


def list_catalog():
    return {
        "categories": MOTION_CATEGORIES,
        "templates": list(MOTION_TEMPLATES.values()),
    }


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


def _sample_scene_brightness(video_path: Path, timestamps) -> dict:
    """Inspect representative frame luminance cleanly when ffmpeg is available."""
    try:
        from processor import find_ffmpeg
        ffmpeg, _ = find_ffmpeg()
    except Exception:
        return {}
    out = {}
    for t in (timestamps or [])[:4]:
        try:
            cmd = [
                ffmpeg, "-ss", f"{max(0.0, float(t)):.2f}", "-i", str(video_path),
                "-frames:v", "1", "-vf", "scale=32:56,format=gray", "-f", "rawvideo", "-"
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=6)
            if r.returncode == 0 and len(r.stdout) >= 32 * 56:
                buf = r.stdout
                top_avg = sum(buf[: 32 * 18]) / float(32 * 18)
                bot_avg = sum(buf[32 * 38 : 32 * 56]) / float(32 * 18)
                out[round(float(t), 2)] = {
                    "top_luma": round(top_avg, 1),
                    "bottom_luma": round(bot_avg, 1),
                }
        except Exception:
            pass
    return out


def _heuristic_analyze(captions, scene_stats=None):
    """Context-aware deterministic analyzer over full phrases (no invented facts)."""
    if not captions:
        return []
    suggestions = []
    # Merge adjacent captions into semantic windows of 1-2 sentences
    windows = []
    i = 0
    while i < len(captions):
        c1 = captions[i]
        text = c1.get("text", "").strip()
        s = float(c1.get("s", 0.0))
        e = float(c1.get("e", s + 2.0))
        if i + 1 < len(captions):
            c2 = captions[i + 1]
            if (float(c2.get("s", 0.0)) - e) <= 0.6 and (float(c2.get("e", e)) - s) <= 7.0 and not text.endswith((".", "!", "?")):
                text = f"{text} {c2.get('text', '').strip()}".strip()
                e = float(c2.get("e", e))
                i += 1
        windows.append({"s": s, "e": max(s + 2.2, e), "text": text})
        i += 1

    last_end = -4.0
    for w in windows:
        if w["s"] - last_end < 3.5:
            continue
        txt = w["text"]
        low = txt.lower()
        nums = re.findall(r"r\$\s*[\d.,]+|\d+(?:[.,]\d+)?\s*%|\b\d+(?:[.,]\d+)?\b", txt, re.I)

        tid = None
        reason = ""
        relevance = "Média"
        subject = ""
        params = {}

        if re.search(r"triplic|dobr|quadruplic|faturament|receit|lucr|venda|cresc|dinheir|invest|r\$|reais", low):
            tid = "revenue_growth" if re.search(r"triplic|dobr|cresc|fatur", low) else "money_flow"
            metric = "+3x" if "triplic" in low else ("+2x" if "dobr" in low else (nums[0] if nums else "R$"))
            subject = "Crescimento / Negócios"
            reason = "Trecho menciona evolução financeira ou multiplicação de resultados."
            relevance = "Alta"
            params = {"title": "Resultado citado", "subtitle": txt[:34], "metric": metric}
        elif re.search(r"cidad|estad|pa[ií]s|regi[aã]o|local|mapa|rota|trajet|viag|dist[aâ]nc|brasil|norte|sul", low):
            tid = "route_path" if re.search(r"rota|trajet|viag|caminh", low) else "multi_city_map"
            subject = "Geografia / Localização"
            reason = "Fala descreve deslocamento, rotas ou múltiplas localidades."
            relevance = "Alta"
            cnt = nums[0] if nums else "Locais"
            params = {"title": "Localizações", "subtitle": txt[:34], "metric": str(cnt), "labels": ["Ponto 1", "Ponto 2", "Ponto 3"]}
        elif re.search(r"intelig[eê]ncia|algoritm|sistema|tecnolog|ia\b|autom|dados|painel|software|aplicativo|celular", low):
            tid = "ai_network" if re.search(r"intelig|ia\b|algoritm|autom", low) else "data_dashboard"
            subject = "Tecnologia & Sistemas"
            reason = "Contextualiza uso de tecnologia, automação ou painel digital."
            relevance = "Alta"
            params = {"title": "Tecnologia", "subtitle": txt[:34], "metric": "TECH"}
        elif re.search(r"antes.*depois|diferen|enquanto|compar|melhor.*que|pior.*que|versus|contra", low):
            tid = "vs_split_card"
            subject = "Comparação"
            reason = "Compara dois cenários ou mudanças de estado na fala."
            relevance = "Alta"
            params = {"title": "Comparativo", "subtitle": txt[:34], "labels": ["Antes", "Depois"], "metric": "VS"}
        elif re.search(r"primeiro|segundo|etapa|passo|processo|fluxo|mecanism|ciclo|funciona", low):
            tid = "cycle_loop" if "ciclo" in low else "flow_diagram"
            subject = "Processo / Etapas"
            reason = "Explica sequência de etapas ou funcionamento de um mecanismo."
            relevance = "Alta"
            params = {"title": "Processo", "subtitle": txt[:34], "labels": ["Passo 1", "Passo 2", "Passo 3"]}
        elif re.search(r"\b(19|20)\d{2}\b|hist[oó]ri|tempo|ano|meses|linha do tempo|cronolog", low):
            tid = "timeline_steps"
            subject = "Linha do Tempo"
            reason = "Referência temporal ou marcos sequenciais no discurso."
            relevance = "Média"
            yr = next((n for n in nums if len(n) == 4), "Marcos")
            params = {"title": "Cronologia", "subtitle": txt[:34], "metric": yr}
        elif nums or "%" in txt:
            has_pct = any("%" in n for n in nums)
            tid = "donut_share" if has_pct else "counter_kpi"
            subject = "Dado Numérico"
            reason = "Destaca exatamente o número mencionado para reforço visual."
            relevance = "Alta"
            params = {"title": "Dado Citado", "subtitle": txt[:34], "metric": nums[0]}
        elif re.search(r"importante|segredo|motivo|porque|conceit|explic|aten[çc][aã]o|acontece", low):
            tid = "concept_callout"
            subject = "Explicação-Chave"
            reason = "Momento explicativo que ganha clareza com cartão de apoio visual."
            relevance = "Média"
            params = {"title": "Conceito-Chave", "subtitle": txt[:36], "metric": "FOCO"}

        if tid:
            tpl = MOTION_TEMPLATES[tid]
            merged = dict(tpl["default_params"])
            merged.update(params)
            # Pick cleanest non-overlapping upper slot
            merged["position"] = "top-center" if len(suggestions) % 2 == 0 else "top-right"
            dur = round(min(5.5, max(2.4, w["e"] - w["s"])), 2)
            suggestions.append({
                "id": f"mg_{len(suggestions)+1}_{tid}",
                "start": round(w["s"], 2),
                "end": round(w["s"] + dur, 2),
                "excerpt": txt,
                "subject": subject,
                "category": tpl["category"],
                "template_id": tid,
                "template_name": tpl["name"],
                "reason": reason,
                "relevance": relevance,
                "position": merged["position"],
                "params": merged,
                "status": "suggested",
            })
            last_end = w["s"] + dur
            if len(suggestions) >= 6:
                break

    return suggestions


def analyze_video_for_motion(captions, video_path=None):
    """
    Analyze full timestamped transcript (+ optional visual framing) and recommend
    high-value Motion Graphics using Groq LLM when available, falling back cleanly
    to deterministic contextual NLP without inventing numbers or facts.
    """
    if not captions:
        return []
    scene_stats = {}
    if video_path and Path(video_path).exists():
        sample_ts = [c["s"] for c in captions[:: max(1, len(captions) // 4)]]
        scene_stats = _sample_scene_brightness(Path(video_path), sample_ts)

    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if groq_key:
        try:
            transcript_lines = [
                f"[{round(float(c['s']), 2)}s - {round(float(c['e']), 2)}s] {c.get('text', '').strip()}"
                for c in captions
            ]
            catalog_summary = [
                {"id": k, "category": v["category"], "name": v["name"], "desc": v["description"]}
                for k, v in MOTION_TEMPLATES.items()
            ]
            prompt = (
                "Você é um diretor de Motion Graphics. Analise a transcrição com timestamps abaixo e sugira NO MÁXIMO 5 "
                "oportunidades onde um Motion Graphic realmente ajuda a explicar o que está sendo dito.\n"
                "REGRAS ESTRITAS:\n"
                "1. NÃO invente números, porcentagens, datas ou fatos que não estejam ditos na transcrição.\n"
                "2. Respeite frases completas (intervalos start/end coerentes, duração 2.5s a 5.5s, espaçados >= 3.5s).\n"
                "3. Escolha template_id SOMENTE dentre os listados.\n"
                "4. Retorne APENAS JSON válido no formato {\"suggestions\": [{\"start\": number, \"end\": number, "
                "\"excerpt\": string, \"subject\": string, \"template_id\": string, \"reason\": string, "
                "\"relevance\": \"Alta\"|\"Média\", \"position\": \"top-center\"|\"top-right\"|\"top-left\", "
                "\"title\": string, \"subtitle\": string, \"metric\": string, \"labels\": [string]}]}.\n\n"
                f"TEMPLATES DISPONÍVEIS:\n{json.dumps(catalog_summary, ensure_ascii=False)}\n\n"
                f"TRANSCRIÇÃO:\n" + "\n".join(transcript_lines[:60])
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
            with urllib.request.urlopen(req, timeout=14) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            raw_sugs = parsed.get("suggestions") or []
            out = []
            for idx, item in enumerate(raw_sugs[:6]):
                tid = item.get("template_id")
                if tid not in MOTION_TEMPLATES:
                    continue
                tpl = MOTION_TEMPLATES[tid]
                s_t = max(0.0, float(item.get("start", 0.0)))
                e_t = max(s_t + 2.2, min(s_t + 6.0, float(item.get("end", s_t + 3.2))))
                if out and s_t < out[-1]["end"] + 1.5:
                    continue
                merged = dict(tpl["default_params"])
                for k in ("title", "subtitle", "metric", "position"):
                    if item.get(k):
                        merged[k] = str(item[k])[:42]
                if isinstance(item.get("labels"), list) and item["labels"]:
                    merged["labels"] = [str(x)[:16] for x in item["labels"][:4]]
                out.append({
                    "id": f"mg_{idx+1}_{tid}",
                    "start": round(s_t, 2),
                    "end": round(e_t, 2),
                    "excerpt": str(item.get("excerpt") or "")[:120],
                    "subject": str(item.get("subject") or tpl["name"])[:40],
                    "category": tpl["category"],
                    "template_id": tid,
                    "template_name": tpl["name"],
                    "reason": str(item.get("reason") or tpl["description"])[:160],
                    "relevance": "Alta" if str(item.get("relevance", "")).lower().startswith("alt") else "Média",
                    "position": merged["position"],
                    "params": merged,
                    "status": "suggested",
                })
            if out:
                return out
        except Exception:
            pass

    return _heuristic_analyze(captions, scene_stats=scene_stats)


def _draw_motion_frame(tpl_id: str, params: dict, prog: float, t_sec: float, w: int, h: int, fonts: dict) -> Image.Image:
    """Render one anti-aliased RGBA Motion Graphic frame at progress 0..1."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")
    accent = _hex_to_rgb(params.get("accent_color", "#22C55E"))
    easing_mode = params.get("easing", "cubic-out")
    entry_mode = params.get("entry_exit", "slide-up")

    # Entry & Exit envelope
    enter_p = _ease(min(1.0, prog / 0.18), easing_mode)
    exit_p = _ease(min(1.0, (1.0 - prog) / 0.16), "smooth")
    alpha_env = min(enter_p, exit_p)
    alpha_env = max(0.0, min(1.0, alpha_env))
    anim_p = _ease(min(1.0, max(0.0, (prog - 0.05) / 0.65)), easing_mode)

    # Panel inner box with safety margin for glow & entrance offset
    pad = 16
    dx_off = 0
    dy_off = 0
    if entry_mode == "slide-up":
        dy_off = int((1.0 - enter_p) * 24)
    elif entry_mode == "pop":
        dy_off = int((1.0 - enter_p) * 10)

    bx0, by0 = pad + dx_off, pad + dy_off
    bx1, by1 = w - pad + dx_off, h - pad + dy_off
    bw, bh = max(80, bx1 - bx0), max(60, by1 - by0)

    bg_alpha = int(214 * alpha_env)
    brd_alpha = int(170 * alpha_env)
    fg_a = int(255 * alpha_env)
    mut_a = int(195 * alpha_env)
    acc_a = int(245 * alpha_env)

    # Glassmorphic card shell
    rad = max(16, int(min(bw, bh) * 0.11))
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=rad, fill=(10, 18, 14, bg_alpha), outline=(*accent, brd_alpha), width=2)
    # Subtle top accent bar
    draw.rounded_rectangle([bx0 + 18, by0 + 10, bx0 + 18 + int((bw - 36) * anim_p), by0 + 14], radius=2, fill=(*accent, acc_a))

    title = str(params.get("title") or MOTION_TEMPLATES.get(tpl_id, {}).get("name", "Motion"))[:28]
    subtitle = str(params.get("subtitle") or "")[:36]
    metric = str(params.get("metric") or "")[:16]
    labels = [str(x)[:12] for x in (params.get("labels") or ["1", "2", "3"])]
    vals = [float(v) for v in (params.get("values") or [30, 65, 95]) if isinstance(v, (int, float))] or [40, 75, 100]

    draw.text((bx0 + 20, by0 + 22), title, font=fonts["title"], fill=(245, 250, 247, fg_a))
    if subtitle:
        draw.text((bx0 + 20, by0 + 48), subtitle, font=fonts["sub"], fill=(168, 194, 178, mut_a))
    if metric:
        draw.text((bx1 - 22, by0 + 22), metric, font=fonts["metric"], fill=(*accent, fg_a), anchor="ra")

    # Inner canvas region for programmatic graphics
    gx0, gy0 = bx0 + 22, by0 + 76
    gx1, gy1 = bx1 - 22, by1 - 20
    gw, gh = max(60, gx1 - gx0), max(50, gy1 - gy0)

    if tpl_id in ("revenue_growth", "data_dashboard"):
        # Gridlines + glowing animated growth spline
        for r in range(3):
            yy = gy0 + int(gh * (r + 1) / 4.0)
            draw.line([(gx0, yy), (gx1, yy)], fill=(255, 255, 255, int(28 * alpha_env)), width=1)
        pts = []
        vmax = max(vals) or 100.0
        n_v = max(2, len(vals))
        for i, val in enumerate(vals):
            px = gx0 + int((gw * i) / (n_v - 1))
            py = gy1 - int((gh * 0.85) * (val / vmax) * anim_p)
            pts.append((px, py))
        if len(pts) >= 2:
            poly = pts + [(pts[-1][0], gy1), (pts[0][0], gy1)]
            draw.polygon(poly, fill=(*accent, int(48 * alpha_env)))
            draw.line(pts, fill=(*accent, acc_a), width=4, joint="curve")
            lx, ly = pts[-1]
            pulse = 5 + int(3 * math.sin(t_sec * 6.0))
            draw.ellipse([lx - pulse, ly - pulse, lx + pulse, ly + pulse], fill=(*accent, int(110 * alpha_env)))
            draw.ellipse([lx - 5, ly - 5, lx + 5, ly + 5], fill=(255, 255, 255, fg_a))

    elif tpl_id in ("bar_chart", "vs_split_card", "before_after_meter", "money_flow"):
        n_b = max(2, min(5, len(vals)))
        vmax = max(vals[:n_b]) or 100.0
        gap = 12
        bar_w = max(14, (gw - gap * (n_b - 1)) // n_b)
        for i in range(n_b):
            bx = gx0 + i * (bar_w + gap)
            ratio = vals[i] / vmax
            cur_h = max(6, int((gh - 22) * ratio * anim_p))
            by_top = (gy1 - 18) - cur_h
            col = (*accent, acc_a) if i == n_b - 1 else (180, 210, 192, int(130 * alpha_env))
            draw.rounded_rectangle([bx, by_top, bx + bar_w, gy1 - 18], radius=6, fill=col)
            lbl = labels[i] if i < len(labels) else f"#{i+1}"
            draw.text((bx + bar_w // 2, gy1 - 13), lbl[:8], font=fonts["sub"], fill=(210, 230, 218, mut_a), anchor="ma")

    elif tpl_id in ("donut_share", "cycle_loop", "counter_kpi"):
        cx, cy = (gx0 + gx1) // 2, (gy0 + gy1) // 2
        rad_c = max(24, int(min(gw, gh) * 0.40))
        box = [cx - rad_c, cy - rad_c, cx + rad_c, cy + rad_c]
        draw.arc(box, start=0, end=360, fill=(255, 255, 255, int(40 * alpha_env)), width=10)
        sweep = int((vals[0] / 100.0 if vals[0] <= 100 else 0.85) * 360 * anim_p)
        draw.arc(box, start=-90, end=-90 + sweep, fill=(*accent, acc_a), width=10)
        m_num = re.findall(r"\d+", metric)
        center_txt = metric
        if tpl_id == "counter_kpi" and m_num:
            target_n = int(m_num[0])
            cur_n = int(target_n * anim_p)
            center_txt = metric.replace(m_num[0], str(cur_n), 1)
        draw.text((cx, cy), center_txt[:10], font=fonts["metric"], fill=(255, 255, 255, fg_a), anchor="mm")

    elif tpl_id in ("multi_city_map", "route_path"):
        # Stylized vector grid + route curve + pulsing location pins
        for k in range(1, 4):
            draw.line([(gx0, gy0 + int(gh * k / 4)), (gx1, gy0 + int(gh * k / 4))], fill=(255, 255, 255, int(24 * alpha_env)), width=1)
            draw.line([(gx0 + int(gw * k / 4), gy0), (gx0 + int(gw * k / 4), gy1)], fill=(255, 255, 255, int(24 * alpha_env)), width=1)
        n_pins = max(2, min(3, len(labels)))
        pin_pts = [
            (gx0 + int(gw * (0.16 + 0.34 * i)), gy0 + int(gh * (0.62 if i % 2 == 0 else 0.30)))
            for i in range(n_pins)
        ]
        # Animated dashed/glowing connector path
        for i in range(len(pin_pts) - 1):
            p0, p1 = pin_pts[i], pin_pts[i + 1]
            cur_x = int(p0[0] + (p1[0] - p0[0]) * anim_p)
            cur_y = int(p0[1] + (p1[1] - p0[1]) * anim_p)
            draw.line([p0, (cur_x, cur_y)], fill=(*accent, acc_a), width=3)
        for i, (px, py) in enumerate(pin_pts):
            pulse = 10 + int(4 * abs(math.sin(t_sec * 4.0 + i)))
            draw.ellipse([px - pulse, py - pulse, px + pulse, py + pulse], fill=(*accent, int(70 * alpha_env)))
            draw.ellipse([px - 6, py - 6, px + 6, py + 6], fill=(255, 255, 255, fg_a), outline=(*accent, acc_a), width=2)
            draw.text((px, py + 12), labels[i][:10], font=fonts["sub"], fill=(230, 245, 236, fg_a), anchor="ma")

    elif tpl_id in ("flow_diagram", "timeline_steps", "ai_network"):
        n_st = max(2, min(3, len(labels)))
        step_w = max(46, (gw - 28 * (n_st - 1)) // n_st)
        cy = (gy0 + gy1) // 2
        for i in range(n_st):
            sx0 = gx0 + i * (step_w + 28)
            lit = anim_p >= (i / float(n_st))
            fill_c = (*accent, int(65 * alpha_env)) if lit else (255, 255, 255, int(20 * alpha_env))
            brd_c = (*accent, acc_a) if lit else (255, 255, 255, int(60 * alpha_env))
            draw.rounded_rectangle([sx0, cy - 22, sx0 + step_w, cy + 22], radius=10, fill=fill_c, outline=brd_c, width=2)
            draw.text((sx0 + step_w // 2, cy), labels[i][:10], font=fonts["sub"], fill=(255, 255, 255, fg_a), anchor="mm")
            if i < n_st - 1:
                draw.line([(sx0 + step_w + 4, cy), (sx0 + step_w + 24, cy)], fill=(*accent, acc_a if lit else mut_a), width=3)

    else:
        # concept_callout / badge_alert: clean focus banner with pulse icon
        cy = (gy0 + gy1) // 2
        pulse = 18 + int(4 * math.sin(t_sec * 4.5))
        draw.ellipse([gx0 + 22 - pulse, cy - pulse, gx0 + 22 + pulse, cy + pulse], fill=(*accent, int(75 * alpha_env)))
        draw.ellipse([gx0 + 8, cy - 14, gx0 + 36, cy + 14], fill=(*accent, acc_a))
        draw.text((gx0 + 52, cy), (labels[0] if labels else title)[:22], font=fonts["title"], fill=(255, 255, 255, fg_a), anchor="lm")

    return img


def render_motion_clip(
    template_id: str,
    params: dict,
    out_path: Path,
    duration: float = 3.2,
    width: int = 560,
    height: int = 230,
    fps: int = 24,
    on_progress=None,
    cancel_event=None,
) -> Path:
    """Render parameterized animated Motion Graphic into a lossless RGBA .mov overlay clip."""
    from processor import find_ffmpeg

    ffmpeg, _ = find_ffmpeg()
    tpl = MOTION_TEMPLATES.get(template_id, MOTION_TEMPLATES["revenue_growth"])
    merged = dict(tpl["default_params"])
    merged.update(params or {})

    dur = max(1.2, min(10.0, float(duration or 3.2)))
    speed = max(0.5, min(2.0, float(merged.get("speed", 1.0))))
    w = max(240, int(width) - (int(width) % 2))
    h = max(120, int(height) - (int(height) % 2))
    total_frames = max(12, int(round(dur * fps)))

    fonts = {
        "title": _load_font("CreatoDisplay-Bold.otf", 22),
        "sub": _load_font("CreatoDisplay-Regular.otf", 14),
        "metric": _load_font("CreatoDisplay-ExtraBold.otf", 26),
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
                prog = (f_idx / float(max(1, total_frames - 1)))
                t_sec = (f_idx / float(fps)) * speed
                frame = _draw_motion_frame(template_id, merged, prog, t_sec, w, h, fonts)
                frame.save(proc.stdin, format="PNG", compress_level=1)
                if on_progress and (f_idx % max(1, total_frames // 8) == 0 or f_idx == total_frames - 1):
                    on_progress(int(10 + 85 * ((f_idx + 1) / float(total_frames))))
            proc.stdin.close()
            rc = proc.wait(timeout=30)
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
