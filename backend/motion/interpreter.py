"""
A. Visual Interpreter
Analyzes spoken transcript + surrounding context (`prev_text`, `next_text`),
classifies speech act (filtering out greetings, filler, transitions, and vague chat),
extracts concise visual insight (never raw truncated sentences!), concrete entities,
numbers, causal relations, visual metaphor, and animated narrative beats.
"""
import json
import os
import re
import textwrap
import urllib.request

INTENTS = (
    "money_growth",
    "security_tactical",
    "ai_architecture",
    "geo_journey",
    "value_comparison",
    "machine_mechanics",
    "business_scale",
    "historical_chronology",
    "scientific_principle",
    "process_transformation",
    "educational_craft",
    "conceptual_focus",
)


def extract_numbers(text: str) -> list:
    return re.findall(
        r"r\$\s*[\d.,]+(?:\s*(?:mil|mi|milh[oõ]es|bi|k))?|\d+(?:[.,]\d+)?\s*%|\b(?:1[0-9]{3}|20[0-9]{2})\b|\b\d+(?:[.,]\d+)?\b",
        text or "",
        re.I,
    )


def _is_non_visual_filler(txt: str) -> tuple:
    """Detect greetings, personal remarks, transitions, and empty conversational padding."""
    low = re.sub(r"\s+", " ", (txt or "").strip().lower()).strip(" .!?,;")
    if not low:
        return True, "trecho vazio"

    words = low.split()
    has_num = bool(extract_numbers(low))
    # Explicit non-visual conversational patterns
    if re.search(
        r"(?:^(?:oi|ol[áa]|fala pessoal|tudo bem|bom dia|boa tarde|boa noite|e a[ií]|bem-vindo|"
        r"deixa eu te falar|presta aten[çc][aã]o|escuta s[óo]|antes de continuar|"
        r"como eu tava dizendo|eu acho que|na minha opini[aã]o|enfim|ent[aã]o gente)\b|"
        r"se inscrev|curte o v[ií]deo|deixa o like|comenta aqui|compartilha)",
        low,
    ) and not has_num and len(words) < 12:
        return True, "saudação/transição/CTA sem valor visual"

    if len(words) <= 5 and not has_num and not re.search(
        r"polic|m[áa]quin|motor|[áa]tom|s[ée]cul|viag|fatur|r\$|%|cresc|ia\b|caligraf|compar|process", low
    ):
        return True, "frase curta sem informação explicativa"

    if re.search(r"^(?:isso [ée] muito|eu gosto muito|que legal|caramba|nossa|exatamente|com certeza)", low) and not has_num:
        return True, "observação pessoal sem dado visual"

    return False, ""


def _craft_concise_copy(txt: str, intent: str, nums: list, places: list) -> tuple:
    """
    Produce crisp, designer-ready (headline, accent, concise_tag) that NEVER
    slices raw transcripts mid-word ('mês ne', 'viaturas co').
    """
    raw = re.sub(r"\s+", " ", (txt or "").strip()).strip(" .!?")
    cleaned = re.sub(
        r"^(?:então|olha só|veja bem|é uma|é um|isso é|esse é|essa é|aqui tem|"
        r"a gente faz|a gente|nós fazemos|você faz|você pode|na física quântica|veja o|no nosso)\s+",
        "",
        raw,
        flags=re.I,
    ).strip()

    if intent == "geo_journey" and len(places) >= 2:
        head = places[0].upper()[:16]
        acc = f"→ {' → '.join(places[1:3])}"[:22]
        return head, acc, f"Rota entre {len(places)} destinos"

    if intent == "value_comparison" and len(nums) >= 2:
        return nums[0].upper()[:12], f"vs {nums[1].upper()}"[:16], "Comparativo de valor"

    if intent == "historical_chronology" and len(nums) >= 2:
        return f"{nums[0]} → {nums[-1]}"[:20], "linha histórica", "Marcos cronológicos"

    if intent == "money_growth" and nums:
        return nums[0].upper()[:16], "acima da meta" if "acima" in raw.lower() else "faturamento", "Marco financeiro"

    words = [w.strip(".,!?;:") for w in cleaned.split() if w.strip(".,!?;:")]
    # Drop trailing loose prepositions/articles cleanly
    stop_tail = {"de", "do", "da", "dos", "das", "e", "o", "a", "um", "uma", "em", "no", "na", "por", "para", "com", "que"}
    h_words = words[:3]
    while len(h_words) > 1 and h_words[-1].lower() in stop_tail:
        h_words.pop()
    head = " ".join(h_words).upper()

    rest = words[len(h_words) : len(h_words) + 3]
    while len(rest) > 1 and rest[-1].lower() in stop_tail:
        rest.pop()
    acc_raw = " ".join(rest).lower()
    w_acc = textwrap.wrap(acc_raw, width=22, break_long_words=False) if acc_raw else []
    acc = w_acc[0] if w_acc else acc_raw[:22]

    # Concise insight subtitle <= 32 chars on whole word boundaries (zero truncated transcripts!)
    tag_words = words[:5]
    while len(tag_words) > 2 and tag_words[-1].lower() in stop_tail:
        tag_words.pop()
    tag = " ".join(tag_words)
    if len(tag) > 32:
        wr = textwrap.wrap(tag, width=32, break_long_words=False)
        tag = wr[0] if wr else tag[:32]
    w_hd = textwrap.wrap(head, width=24, break_long_words=False) if head else []
    return (w_hd[0] if w_hd else head[:24]), acc, tag


def _clean_clauses(text: str, max_items: int = 3, max_chars: int = 24) -> list:
    parts = re.split(r"[,;:.!?]+|\b(?:e depois|depois|então|mas|porém|enquanto|para que|onde|até|vs\.?|versus|contra)\b", text or "", flags=re.I)
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
    low = txt.lower()
    nums = extract_numbers(txt)
    places = [
        m.strip(".,!?;:")
        for m in re.findall(r"\b[A-ZÀ-Ú][a-zà-ú]{1,}(?:\s+[A-ZÀ-Ú][a-zà-ú]{1,})*", " ".join(txt.split()[1:]) if len(txt.split()) > 1 else "")
        if m.lower() not in ("agora", "antes", "depois", "passo", "hoje", "então", "isso", "quando", "plano")
    ]

    skip, skip_reason = _is_non_visual_filler(txt)

    if re.search(r"polic|opera[çc][aã]o|viatur|cerco|per[ií]metr|delegac|investiga|suspeit|seguran[çc]a|t[áa]tic|alvo", low):
        intent = "security_tactical"
        metaphor = "Varredura tática de radar com perímetro delimitado e vetores convergindo ao alvo."
    elif re.search(r"m[áa]quin|motor|engrenag|pist[aã]o|cilindr|press[aã]o|turbina|mecanism|interno|torque|eixo", low):
        intent = "machine_mechanics"
        metaphor = "Corte técnico animado com engrenagens interligadas transmitindo movimento ao pistão."
    elif re.search(r"[áa]tom|mol[ée]cul|el[ée]tron|energ|onda|frequ[êe]nc|experimento|f[íi]sic|qu[íi]mic|biolog|c[ée]lul|gravidade|rea[çc][aã]o|cient[íi]f", low):
        intent = "scientific_principle"
        metaphor = "Órbitas atômicas tridimensionais emitindo energia modulada em onda física."
    elif re.search(r"s[ée]cul|guerra|imp[ée]rio|revolu[çc]|hist[óo]ri|d[ée]cada|fundad|constitui|regime|\b1[5-9]\d{2}\b", low):
        intent = "historical_chronology"
        metaphor = "Linha temporal luminosa marcando os anos-chave e a virada histórica."
    elif re.search(r"\bintelig[eê]ncia\b|\bia\b|rede neural|algoritm|processamento|dados|sistema digital", low):
        intent = "ai_architecture"
        metaphor = "Núcleo 3D octaédrico recebendo fluxos de entrada e distribuindo sinais neurais."
    elif re.search(r"viag|cidad|aeroporto|trajet|rota|sa[ií]ndo de|indo para|chegando em|pa[ií]s|fronteira", low) or len(places) >= 2:
        intent = "geo_journey"
        metaphor = "Arcos geográficos luminosos ligando as cidades citadas sobre curvas cartográficas."
    elif re.search(r"compar|versus|\bvs\b|enquanto|diferen[çc]|antes.*agora|antes.*depois", low):
        intent = "value_comparison"
        metaphor = "Escala proporcional flutuante contrastando os dois valores e revelando a diferença."
    elif re.search(r"fatur|receit|lucr|dinheir|r\$|reais|caixa|invest", low):
        intent = "money_growth"
        metaphor = "Moedas 3D metálicas subindo além da linha de meta financeira."
    elif re.search(r"cresc|empres|escal|expans|triplic|dobr|mercado|cliente", low):
        intent = "business_scale"
        metaphor = "Colunas 3D em perspectiva ascendendo com curva de aceleração."
    elif re.search(r"transform|metamorfose|etapa|processo|fluxo|passo|converte|mat[ée]ria|refinad", low):
        intent = "process_transformation"
        metaphor = "Fluxo catalítico transformando matéria inicial em estrutura final refinada."
    elif re.search(r"caligraf|imprim|escrev|caderno|papel", low):
        intent = "educational_craft"
        metaphor = "Traço cursivo animado desenhado em tempo real sobre guias de treino."
    else:
        intent = "conceptual_focus"
        metaphor = "Tipografia cinética com revelação por máscara e acento visual integrado."

    head, acc, concise_tag = _craft_concise_copy(txt, intent, nums, places)
    clauses = _clean_clauses(txt, max_items=3, max_chars=24)

    # Smart domain label extraction
    if intent == "value_comparison":
        vs_parts = [
            re.sub(r"\s*(?:de\s+)?r\$\s*[\d.,]+.*$", "", re.sub(r"^(?:comparando\s+dois\s+valores:\s*)", "", p.strip(" ,.;:!?"), flags=re.I), flags=re.I).strip()
            for p in re.split(r"\b(?:vs\.?|versus|contra|enquanto)\b", txt, maxsplit=1, flags=re.I)
            if p.strip()
        ]
        if len(vs_parts) >= 2:
            clauses = [vs_parts[0][:22] or "Opção A", vs_parts[1][:22] or "Opção B"]
    elif intent == "process_transformation":
        tr = re.split(r"\b(?:converte|transforma)\b", txt, maxsplit=1, flags=re.I)
        if len(tr) >= 2:
            sub_p = re.split(r"\b(?:em|para)\b", tr[1], maxsplit=1, flags=re.I)
            if len(sub_p) >= 2:
                clauses = [sub_p[0].strip(" .")[:18], "Catalisador", sub_p[1].strip(" .")[:18]]
    elif intent == "historical_chronology" and len(nums) >= 2:
        clauses = [n for n in nums[:4]]

    return {
        "central_subject": head,
        "accent_phrase": acc,
        "concise_tag": concise_tag,
        "narrative_intent": intent,
        "speech_act": "non_visual" if skip else "visual_explanation",
        "skip_reason": skip_reason,
        "should_render": not skip,
        "concrete_entities": (places or clauses)[:4],
        "abstract_concepts": clauses[:3],
        "extracted_numbers": nums[:4],
        "places": places[:4],
        "visual_metaphor": metaphor,
        "narrative_beats": [
            {"phase": "build", "t0": 0.0, "t1": 0.30, "goal": "Construção espacial"},
            {"phase": "action", "t0": 0.25, "t1": 0.78, "goal": metaphor},
            {"phase": "climax", "t0": 0.74, "t1": 1.0, "goal": "Síntese e saída"},
        ],
        "complexity": "high" if (len(nums) >= 2 or intent in ("machine_mechanics", "security_tactical", "scientific_principle", "geo_journey", "historical_chronology")) else "medium",
    }


def interpret_segment(text: str, prev_text: str = "", next_text: str = "", frame_info: dict = None) -> dict:
    """Contextual Visual Interpreter (LLM + PT-BR semantic fallback with narrative skip gate)."""
    base = _heuristic_interpret(text, prev_text, next_text)
    if not base["should_render"]:
        return base

    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if not groq_key:
        return base

    try:
        sys_msg = (
            "Você é o Visual Interpreter de um estúdio premiado de Motion Design.\n"
            "Avalie a fala NO CONTEXTO e decida: (1) se realmente precisa de Motion Graphic (`should_render`: false para cumprimentos, opiniões vagas ou frases de ligação!) "
            "e (2) se precisar, planeje manchete curta (2-3 palavras, SEM truncar frases!), números reais, entidades e metáfora visual.\n"
            f"Intents válidos: {list(INTENTS)}.\n"
            "Retorne APENAS JSON: {\"should_render\": bool, \"skip_reason\": string, \"central_subject\": string, \"accent_phrase\": string, "
            "\"concise_tag\": string, \"narrative_intent\": string, \"concrete_entities\": [string], \"extracted_numbers\": [string], "
            "\"places\": [string], \"visual_metaphor\": string}.\n"
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

        if isinstance(parsed.get("should_render"), bool):
            base["should_render"] = parsed["should_render"]
            if parsed.get("skip_reason"):
                base["skip_reason"] = str(parsed["skip_reason"])[:80]
        if parsed.get("narrative_intent") in INTENTS:
            base["narrative_intent"] = parsed["narrative_intent"]
        if parsed.get("central_subject"):
            cs = str(parsed["central_subject"]).strip()[:22].upper()
            if cs and cs not in ("MOTION", "TEMPLATE", "CENA"):
                base["central_subject"] = cs
        if parsed.get("accent_phrase"):
            base["accent_phrase"] = str(parsed["accent_phrase"]).strip()[:20].lower()
        if parsed.get("concise_tag"):
            base["concise_tag"] = str(parsed["concise_tag"]).strip()[:32]
        for k in ("concrete_entities", "extracted_numbers", "places"):
            if isinstance(parsed.get(k), list) and parsed[k]:
                base[k] = [str(x)[:22] for x in parsed[k][:4]]
        if parsed.get("visual_metaphor"):
            base["visual_metaphor"] = str(parsed["visual_metaphor"])[:140]
    except Exception:
        pass
    return base
