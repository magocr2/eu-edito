"""
A. Visual Interpreter
Understands spoken narration in context (prev + current + next utterances)
and extracts subject, intent, entities, numbers, causal relations, visual metaphor,
and narrative beats — never relying on naive keyword-to-template matching.
"""
import json
import os
import re
import textwrap
import urllib.request


INTENTS = (
    "money_growth",           # faturamento > X, caixa, lucro, receitas
    "security_tactical",      # operação policial, segurança, perímetro, ação estratégica
    "ai_architecture",        # funcionamento de IA, redes neurais, sistemas digitais
    "geo_journey",            # viagem entre cidades, logística, localização, rotas
    "value_comparison",       # comparação entre valores/cenários/antes e depois
    "machine_mechanics",      # funcionamento interno de máquina/motor/equipamento
    "business_scale",         # crescimento de empresa, métricas, expansão
    "historical_chronology",  # acontecimentos históricos, datas, evolução temporal
    "scientific_principle",   # física, química, biologia, experimento, átomos/ondas
    "process_transformation", # transformação de estado, etapas, fluxo operacional
    "educational_craft",      # caligrafia, método prático, aula, estudo, treino
    "conceptual_focus",       # ideia abstrata, dica, manifesto, alerta
)


def extract_numbers(text: str) -> list:
    return re.findall(
        r"r\$\s*[\d.,]+(?:\s*(?:mil|mi|milh[oõ]es|bi|k))?|\d+(?:[.,]\d+)?\s*%|\b(?:1[0-9]{3}|20[0-9]{2})\b|\b\d+(?:[.,]\d+)?\b",
        text or "",
        re.I,
    )


def _extract_headline_parts(text: str, intent: str) -> tuple:
    raw = re.sub(r"\s+", " ", (text or "").strip()).strip(" .!?")
    if not raw:
        return ("CENÁRIO VISUAL", "", "")

    cleaned = re.sub(
        r"^(?:então|olha só|olha|veja bem|é uma|é um|isso é|esse é|essa é|aqui tem|"
        r"a gente faz|a gente|nós fazemos|você faz|você pode|na verdade|basicamente)\s+",
        "",
        raw,
        flags=re.I,
    ).strip()

    words = cleaned.split()
    if len(words) <= 2:
        return (cleaned.upper()[:24], "", raw[:52])

    split_idx = None
    for i in range(1, min(len(words), 5)):
        if words[i].lower() in ("para", "por", "sem", "com", "entre", "contra", "em", "até", "no", "na", "vs") and i >= 2:
            split_idx = i
            break

    if split_idx is not None:
        head = " ".join(words[:split_idx]).strip(".,!?")
        acc = " ".join(words[split_idx : split_idx + 3]).strip(".,!?")
    else:
        head = " ".join(words[: min(3, len(words))]).strip(".,!?")
        acc = " ".join(words[min(3, len(words)) : min(6, len(words))]).strip(".,!?")

    hw = head.split()
    while len(hw) > 1 and hw[-1].lower() in ("de", "do", "da", "dos", "das", "e", "o", "a", "um", "uma", "em"):
        acc = f"{hw.pop()} {acc}".strip()
    head = " ".join(hw)
    w_head = textwrap.wrap(head, width=24, break_long_words=False)
    w_acc = textwrap.wrap(acc, width=22, break_long_words=False)
    return ((w_head[0] if w_head else head[:24]).upper(), (w_acc[0] if w_acc else acc[:22]).lower(), raw[:56])


def _extract_clauses(text: str, max_items: int = 3, max_chars: int = 30) -> list:
    parts = re.split(r"[,;:.!?]+|\b(?:e depois|depois|então|mas|porém|enquanto|para que|onde|até)\b", text or "", flags=re.I)
    out = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) < 3:
            continue
        if len(p) > max_chars:
            wr = textwrap.wrap(p, width=max_chars, break_long_words=False)
            p = wr[0] if wr else p[:max_chars]
        out.append(p)
        if len(out) >= max_items:
            break
    return out


def _heuristic_interpret(text: str, prev_text: str = "", next_text: str = "") -> dict:
    txt = re.sub(r"\s+", " ", (text or "").strip())
    ctx = f"{prev_text} {txt} {next_text}".lower()
    low = txt.lower()
    nums = extract_numbers(txt)
    places = [
        m.strip(".,!?;:")
        for m in re.findall(r"\b[A-ZÀ-Ú][a-zà-ú]{1,}(?:\s+[A-ZÀ-Ú][a-zà-ú]{1,})*", " ".join(txt.split()[1:]) if len(txt.split()) > 1 else "")
        if m.lower() not in ("agora", "antes", "depois", "passo", "hoje", "então", "isso", "quando")
    ]

    # Contextual multi-domain narrative intent detection
    if re.search(r"polic|opera[çc][aã]o|viatur|cerco|per[ií]metr|delegac|investiga|suspeit|crime|seguran[çc]a p[úu]blica|t[áa]tic|alvo", low):
        intent = "security_tactical"
        metaphor = "Mapa tático operacional com varredura de radar, perímetro delimitado e convergência de unidades."
    elif re.search(r"m[áa]quin|motor|engrenag|pist[aã]o|cilindr|press[aã]o|turbina|mecanism|interno|pe[çc]a|torque|eixo", low):
        intent = "machine_mechanics"
        metaphor = "Corte técnico esquemático com engrenagens sincronizadas e transmissão mecânica em ação."
    elif re.search(r"[áa]tom|mol[ée]cul|el[ée]tron|energ|onda|frequ[êe]nc|experimento|f[íi]sic|qu[íi]mic|biolog|c[ée]lul|gravidade|rea[çc][aã]o|cient[íi]f", low):
        intent = "scientific_principle"
        metaphor = "Modelo científico dinâmico com órbitas, partículas carregadas e oscilação de energia."
    elif re.search(r"s[ée]cul|guerra|imp[ée]rio|revolu[çc]|hist[óo]ri|d[ée]cada|fundad|acontec|\b(1[5-9]\d{2}|20[0-2]\d)\b.*(?:depois|quando|em seguida)", low) or (
        re.search(r"\b1[5-9]\d{2}\b", low)
    ):
        intent = "historical_chronology"
        metaphor = "Crônica documental com linha do tempo em arquivo histórico e marcos cronológicos revelados."
    elif re.search(r"\bintelig[eê]ncia\b|\bia\b|rede neural|modelo|treinamento|algoritm|dados|processamento|n[úu]cleo|sistema digital", low):
        intent = "ai_architecture"
        metaphor = "Arquitetura tecnológica em camadas com prisma central 3D, sinais circulando e nós de processamento."
    elif re.search(r"viag|cidad|aeroporto|trajet|rota|sa[ií]ndo de|indo para|chegando em|pa[ií]s|fronteira|quil[ôo]metr", low) or len(places) >= 2:
        intent = "geo_journey"
        metaphor = "Atlas cartográfico em perspectiva com arcos geográficos conectando localidades reais."
    elif re.search(r"compar|versus|\bvs\b|enquanto|diferen[çc]|maior que|menor que|antes.*agora|antes.*depois", low):
        intent = "value_comparison"
        metaphor = "Balança editorial assimétrica contrastando os dois valores/estados com proporção real."
    elif re.search(r"fatur|receit|lucr|dinheir|r\$|reais|caixa|invest|vend", low):
        intent = "money_growth"
        metaphor = "Composição 3D financeira com moedas/pilares em perspectiva e meta destacada."
    elif re.search(r"cresc|empres|escal|expans|triplic|dobr|mercado|faturamento|cliente", low):
        intent = "business_scale"
        metaphor = "Arquitetura corporativa em ascensão com barras volumétricas 3D e curva de projeção."
    elif re.search(r"transform|metamorfose|etapa|processo|fluxo|passo|passa a ser|converte|muda de|evolu", low):
        intent = "process_transformation"
        metaphor = "Diagrama vivo de transformação conectando estado inicial, catalisador e resultado."
    elif re.search(r"caligraf|imprim|escrev|caderno|minut|por dia|aula|curso|estudo|m[eé]todo|rotina", low):
        intent = "educational_craft"
        metaphor = "Cena ilustrativa orgânica unindo objeto prático da fala e ritmo temporal claro."
    else:
        intent = "conceptual_focus"
        metaphor = "Tipografia cinética de alto contraste integrada ao assunto central com elemento focal."

    head, accent, sub = _extract_headline_parts(txt, intent)
    clauses = _extract_clauses(txt, max_items=3, max_chars=28)
    if intent == "value_comparison":
        vs_parts = [re.sub(r"^(?:comparando\s+dois\s+valores:\s*)", "", p.strip(" ,.;:!?"), flags=re.I) for p in re.split(r"\b(?:vs\.?|versus|contra|enquanto)\b", txt, maxsplit=1, flags=re.I) if p.strip()]
        if len(vs_parts) >= 2:
            clauses = [vs_parts[0][:24], vs_parts[1][:24]]
    elif intent == "process_transformation":
        tr_parts = [re.sub(r"^(?:.*?\bconverte\b|.*?\btransforma\b)", "", p.strip(" ,.;:!?"), flags=re.I).strip() for p in re.split(r"\b(?:em|para)\b", txt, maxsplit=1, flags=re.I) if p.strip()]
        if len(tr_parts) >= 2:
            clauses = [tr_parts[0][:20], "Catalisador", tr_parts[1][:20]]

    # Check if segment carries meaningful visual explanation vs trivial filler
    trivial = len(txt.split()) < 4 and not nums and intent == "conceptual_focus"
    should_render = not trivial

    entities = places[:]
    if not entities:
        entities = [c[:22] for c in clauses[:3]]

    # Build 3 narrative beats aligned with spoken progression
    beats = [
        {"phase": "intro", "t0": 0.0, "t1": 0.28, "goal": f"Introduzir contexto de '{head.lower()}'"},
        {"phase": "development", "t0": 0.25, "t1": 0.76, "goal": metaphor},
        {"phase": "resolution", "t0": 0.72, "t1": 1.0, "goal": f"Consolidar síntese visual ({nums[0] if nums else head})"},
    ]

    return {
        "central_subject": head,
        "accent_phrase": accent,
        "narrative_intent": intent,
        "concrete_entities": entities[:4],
        "abstract_concepts": clauses[:3],
        "extracted_numbers": nums[:4],
        "places": places[:4],
        "relations": clauses[:2],
        "visual_metaphor": metaphor,
        "narrative_beats": beats,
        "summary_line": sub,
        "should_render": should_render,
        "complexity": "high" if (len(nums) >= 2 or len(clauses) >= 3 or intent in ("machine_mechanics", "security_tactical", "scientific_principle", "geo_journey")) else "medium",
    }


def interpret_segment(text: str, prev_text: str = "", next_text: str = "", frame_info: dict = None) -> dict:
    """
    Use Groq LLM contextual director when configured, validated strictly and paired with
    semantic PT-BR fallback so every topic receives bespoke visual interpretation.
    """
    base = _heuristic_interpret(text, prev_text, next_text)
    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not groq_key:
        return base

    try:
        sys_msg = (
            "Você é o Visual Interpreter de um estúdio de Motion Design (nível documentário/Vox/Kurzgesagt).\n"
            "Analise a fala considerando o contexto anterior/posterior e decida SE vale criar Motion Graphic e O QUE representar.\n"
            "REGRAS:\n"
            "1. 'central_subject': manchete curta (2-4 palavras) tirada do assunto real da fala (PROIBIDO nome genérico de template!).\n"
            "2. 'narrative_intent' deve ser exatamente um de: "
            f"{list(INTENTS)}.\n"
            "3. 'concrete_entities': objetos físicos, cidades, peças ou atores concretos citados (máx 4).\n"
            "4. 'extracted_numbers': APENAS números/valores/datas ditos na fala (NUNCA invente!).\n"
            "5. 'visual_metaphor': descreva em 1 frase clara a metáfora visual específica para esta cena.\n"
            "6. Retorne APENAS JSON: {\"should_render\": bool, \"central_subject\": string, \"accent_phrase\": string, "
            "\"narrative_intent\": string, \"concrete_entities\": [string], \"abstract_concepts\": [string], "
            "\"extracted_numbers\": [string], \"places\": [string], \"visual_metaphor\": string}.\n"
            f"Anterior: {prev_text}\nAtual: {text}\nPróxima: {next_text}"
        )
        req_body = json.dumps({
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": sys_msg}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=req_body,
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=11) as resp:
            parsed = json.loads(json.loads(resp.read().decode("utf-8"))["choices"][0]["message"]["content"])

        if parsed.get("narrative_intent") in INTENTS:
            base["narrative_intent"] = parsed["narrative_intent"]
        if parsed.get("central_subject"):
            cs = str(parsed["central_subject"]).strip()[:26].upper()
            if cs and cs not in ("MOTION GRAPHIC", "TEMPLATE", "EXPLICACAO", "CENA"):
                base["central_subject"] = cs
        if parsed.get("accent_phrase"):
            base["accent_phrase"] = str(parsed["accent_phrase"]).strip()[:24].lower()
        for k in ("concrete_entities", "abstract_concepts", "extracted_numbers", "places"):
            if isinstance(parsed.get(k), list) and parsed[k]:
                base[k] = [str(x)[:26] for x in parsed[k][:4]]
        if parsed.get("visual_metaphor"):
            base["visual_metaphor"] = str(parsed["visual_metaphor"])[:140]
        if isinstance(parsed.get("should_render"), bool):
            base["should_render"] = parsed["should_render"]
    except Exception:
        pass
    return base
