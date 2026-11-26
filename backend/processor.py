"""
Hogus Studio Web — Video Transcription, Smart Cuts, Impact Zoom & ASS Renderer
Works on NVIDIA GPU (CUDA + NVENC) or CPU fallback for any server/PC.
"""
import ctypes
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"

_FILLERS = {"hã", "ha", "hum", "uhm", "ehm", "ahn", "éé", "eee", "hmm"}
_IMPACT_WORDS = {
    "segredo", "erro", "verdade", "atenção", "atencao", "cuidado", "nunca", "sempre",
    "melhor", "pior", "resultado", "resultados", "dinheiro", "tempo", "rápido", "rapido",
    "importante", "incrível", "incrivel", "descobri", "muda", "transforma", "dica",
    "passo", "regra", "problema", "solução", "solucao", "agora", "hoje", "imagina",
    "porém", "porem", "então", "entao", "olha", "presta", "exclusivo", "funciona",
    "garanto", "pare", "começa", "comeca", "diferença", "diferenca", "lucro",
}

_WHISPER_CACHE = {}


def find_ffmpeg():
    """Locate ffmpeg/ffprobe from environment or system PATH (cloud/container ready)."""
    ffmpeg = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("FFPROBE_PATH") or shutil.which("ffprobe")
    return ffmpeg or "ffmpeg", ffprobe or "ffprobe"


def detect_hardware():
    cores = os.cpu_count() or 4
    ram_gb = 8.0
    if os.name == "nt":
        try:
            class _MEM(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
            m = _MEM()
            m.dwLength = ctypes.sizeof(_MEM)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                ram_gb = round(m.ullTotalPhys / (1024 ** 3), 1)
        except Exception:
            pass
    else:
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        ram_gb = round(int(line.split()[1]) / (1024 ** 2), 1)
                        break
        except Exception:
            pass
        # Check Linux container cgroup memory limit (e.g., 512 MB on Render Free)
        for cg_path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
            try:
                val = Path(cg_path).read_text(encoding="utf-8").strip()
                if val.isdigit():
                    cg_gb = round(int(val) / (1024 ** 3), 2)
                    if 0.1 < cg_gb < ram_gb:
                        ram_gb = cg_gb
                    break
            except Exception:
                pass

    cuda_ready = False
    cuda_compute = "float16"
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            cuda_ready = True
            supported = set(ctranslate2.get_supported_compute_types("cuda"))
            for ct in ("float16", "int8_float16", "int8", "float32"):
                if ct in supported:
                    cuda_compute = ct
                    break
    except Exception:
        pass

    ffmpeg_exe, _ = find_ffmpeg()
    nvenc_ready = False
    try:
        r = subprocess.run([ffmpeg_exe, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=4)
        nvenc_ready = "h264_nvenc" in (r.stdout or "")
    except Exception:
        pass

    if cuda_ready:
        model, device, compute, threads, beam = "large-v3-turbo", "cuda", cuda_compute, min(cores, 6), 5
        label = "GPU NVIDIA (CUDA + NVENC)" if nvenc_ready else "GPU NVIDIA (CUDA)"
    elif ram_gb <= 1.2:
        model, device, compute, threads, beam = "tiny", "cpu", "int8", max(1, min(cores, 2)), 1
        label = f"Modo Econômico ({model} · {ram_gb}GB RAM)"
    elif ram_gb <= 8.5 or cores <= 4:
        model, device, compute, threads, beam = "small", "cpu", "int8", max(2, min(cores, 4)), 1
        label = f"Modo Leve ({model} · {threads} threads)"
    elif ram_gb <= 14.0 or cores <= 8:
        model, device, compute, threads, beam = "medium", "cpu", "int8", max(2, cores - 1), 2
        label = f"Modo Equilibrado ({model} · {threads} threads)"
    else:
        model, device, compute, threads, beam = "large-v3-turbo", "cpu", "int8", min(cores, 8), 3
        label = f"CPU Turbo ({model} · {threads} threads)"

    os.environ["OMP_NUM_THREADS"] = str(threads)
    os.environ["MKL_NUM_THREADS"] = str(threads)
    return {
        "cpu_cores": cores,
        "ram_gb": ram_gb,
        "cuda_ready": cuda_ready,
        "nvenc_ready": nvenc_ready,
        "whisper_model": model,
        "device": device,
        "compute_type": compute,
        "cpu_threads": threads,
        "beam_size": beam,
        "accel_label": label,
    }


def _get_whisper_model(hw):
    from faster_whisper import WhisperModel
    attempts = []
    if hw["cuda_ready"]:
        attempts.append((hw["whisper_model"], "cuda", hw["compute_type"], hw["beam_size"]))
    cpu_model = hw["whisper_model"] if not hw["cuda_ready"] else ("small" if hw["ram_gb"] <= 8.5 else "large-v3-turbo")
    attempts.append((cpu_model, "cpu", "int8", hw["beam_size"] if not hw["cuda_ready"] else 2))

    for m_name, dev, ct, beam in attempts:
        key = (m_name, dev, ct)
        if key in _WHISPER_CACHE:
            return _WHISPER_CACHE[key], beam
        for local_only in (True, False):
            try:
                kw = {"device": dev, "compute_type": ct, "local_files_only": local_only}
                if dev == "cpu":
                    kw["cpu_threads"] = hw["cpu_threads"]
                m = WhisperModel(m_name, **kw)
                _WHISPER_CACHE[key] = m
                return m, beam
            except Exception:
                pass
    raise RuntimeError("Não foi possível carregar o modelo Whisper.")


def probe_video(video_path):
    _, ffprobe = find_ffmpeg()
    cmd = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration:format=duration",
        "-of", "json", str(video_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    data = json.loads(r.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    w = int(stream.get("width") or 1080)
    h = int(stream.get("height") or 1920)
    dur = float(stream.get("duration") or fmt.get("duration") or 0.0)
    return {"width": w, "height": h, "duration": dur}


def transcribe_video(video_path, hw, language="pt"):
    import gc
    ffmpeg, _ = find_ffmpeg()
    # Extract lightweight 16kHz mono WAV so Whisper doesn't decode full HD/4K video frames in RAM
    wav_path = Path(video_path).with_suffix(".16k.wav")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(video_path), "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", str(wav_path)],
            capture_output=True, timeout=120
        )
    except Exception:
        pass
    audio_input = str(wav_path) if (wav_path.exists() and wav_path.stat().st_size > 1000) else str(video_path)

    model, beam = _get_whisper_model(hw)
    segments, info = model.transcribe(
        audio_input,
        language=language or "pt",
        beam_size=beam,
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=(beam > 1),
        initial_prompt="Transcrição em português brasileiro com acentuação e pontuação corretas.",
    )
    words = []
    for seg in segments:
        for w in (seg.words or []):
            txt = (w.word or "").strip()
            if txt:
                words.append({"w": txt, "s": round(float(w.start), 3), "e": round(float(w.end), 3)})
    try:
        wav_path.unlink(missing_ok=True)
    except Exception:
        pass
    if hw.get("ram_gb", 8.0) <= 1.2:
        _WHISPER_CACHE.clear()
        del model
        gc.collect()
    return words, float(getattr(info, "duration", 0.0) or 0.0)


def compute_keep_ranges(words, duration, cuts_enabled=True, rhythm="natural"):
    if not cuts_enabled or not words or duration <= 0.5:
        return [{"s": 0.0, "e": round(duration, 3)}]

    is_firm = (rhythm or "natural").lower() in ("firm", "firme")
    min_gap = 0.24 if is_firm else 0.45
    pad_l = 0.05 if is_firm else 0.09
    pad_r = 0.07 if is_firm else 0.11

    cut_regions = []
    # 1. Remove leading/trailing long silences
    if words[0]["s"] > (0.25 if is_firm else 0.40):
        cut_regions.append((0.0, max(0.0, words[0]["s"] - pad_l)))
    if duration - words[-1]["e"] > (0.35 if is_firm else 0.50):
        cut_regions.append((min(duration, words[-1]["e"] + pad_r), duration))

    # 2. Remove fillers and inter-word pauses >= min_gap
    for i, w in enumerate(words):
        clean = re.sub(r"[^\wà-úÀ-Ú]", "", w["w"].lower())
        if clean in _FILLERS:
            cut_regions.append((max(0.0, w["s"] - 0.02), min(duration, w["e"] + 0.02)))
        if i + 1 < len(words):
            gap = words[i + 1]["s"] - w["e"]
            if gap >= min_gap:
                cs = w["e"] + pad_l
                ce = words[i + 1]["s"] - pad_r
                if ce - cs >= 0.08:
                    cut_regions.append((cs, ce))

    if not cut_regions:
        return [{"s": 0.0, "e": round(duration, 3)}]

    # Merge overlapping cut regions
    cut_regions.sort()
    merged = [list(cut_regions[0])]
    for s, e in cut_regions[1:]:
        if s <= merged[-1][1] + 0.04:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    # Invert to keep ranges
    keep = []
    cursor = 0.0
    for cs, ce in merged:
        if cs - cursor >= 0.20:
            keep.append({"s": round(cursor, 3), "e": round(cs, 3)})
        cursor = max(cursor, ce)
    if duration - cursor >= 0.20:
        keep.append({"s": round(cursor, 3), "e": round(duration, 3)})

    return keep or [{"s": 0.0, "e": round(duration, 3)}]


def map_time_to_edited(t, keep_ranges):
    """Map an original video timestamp to the cut timeline."""
    acc = 0.0
    for seg in keep_ranges:
        s, e = seg["s"], seg["e"]
        if t < s:
            return round(acc, 3)
        if s <= t <= e:
            return round(acc + (t - s), 3)
        acc += (e - s)
    return round(acc, 3)


def build_captions(words, keep_ranges, max_chars=26):
    """Group words into dynamic short captions aligned to the cut timeline."""
    mapped_words = []
    for w in words:
        mid = (w["s"] + w["e"]) / 2.0
        # Skip words that fell inside a cut region
        if not any(seg["s"] - 0.03 <= mid <= seg["e"] + 0.03 for seg in keep_ranges):
            continue
        ms = map_time_to_edited(w["s"], keep_ranges)
        me = map_time_to_edited(w["e"], keep_ranges)
        if me <= ms:
            me = ms + 0.12
        mapped_words.append({"w": w["w"], "s": round(ms, 3), "e": round(me, 3)})

    captions = []
    cur = []
    cur_len = 0
    for w in mapped_words:
        wlen = len(w["w"])
        gap = (w["s"] - cur[-1]["e"]) if cur else 0.0
        if cur and (cur_len + 1 + wlen > max_chars or len(cur) >= 4 or gap > 0.45 or cur[-1]["w"].endswith((".", "!", "?"))):
            captions.append({
                "s": cur[0]["s"],
                "e": cur[-1]["e"],
                "text": " ".join(x["w"] for x in cur),
                "words": cur,
            })
            cur = []
            cur_len = 0
        cur.append(w)
        cur_len += (1 if cur_len else 0) + wlen
    if cur:
        captions.append({
            "s": cur[0]["s"],
            "e": cur[-1]["e"],
            "text": " ".join(x["w"] for x in cur),
            "words": cur,
        })
    return captions


def pick_impact_moments(captions, min_gap_s=6.0, max_ratio=0.30):
    if not captions:
        return []
    scored = []
    for c in captions:
        txt = c["text"]
        sc = 0.0
        if c["s"] <= 3.5:
            sc += 3.0
        if "?" in txt or "!" in txt:
            sc += 2.2
        if re.search(r"\d+|%|reais|mil\b|milh", txt, re.I):
            sc += 2.5
        for wd in re.findall(r"[a-zà-ú]+", txt.lower()):
            if wd in _IMPACT_WORDS:
                sc += 2.0
            elif len(wd) >= 8:
                sc += 0.5
        if sc > 0:
            scored.append((sc, c["s"], c["e"]))
    scored.sort(key=lambda x: (-x[0], x[1]))
    chosen = []
    limit = max(1, int(len(captions) * max_ratio))
    for sc, s, e in scored:
        if len(chosen) >= limit:
            break
        if all(abs(s - cs) >= min_gap_s for cs, _ in chosen):
            chosen.append((s, e))
    chosen.sort(key=lambda x: x[0])
    return chosen


def _hex_to_ass_bgr(hex_color):
    c = (hex_color or "#22C55E").strip().lstrip("#")
    if len(c) != 6:
        c = "22C55E"
    r, g, b = c[0:2], c[2:4], c[4:6]
    return f"&H00{b.upper()}{g.upper()}{r.upper()}&"


def _fmt_ass_time(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _fmt_srt_time(sec):
    sec = max(0.0, float(sec))
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_srt(captions, out_path):
    lines = []
    for idx, c in enumerate(captions, 1):
        lines.append(f"{idx}\n{_fmt_srt_time(c['s'])} --> {_fmt_srt_time(c['e'])}\n{c['text']}\n")
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def generate_ass(captions, out_path, width=1080, height=1920, style_id="classic", accent_hex="#22C55E", pos_y_pct=74):
    styles_cfg = {
        "classic":      {"font": "Creato Display", "size": 74, "upper": True,  "italic": False, "outline": 5, "shadow": 3, "default_accent": "#FFFFFF"},
        "model-07":     {"font": "Georgia",        "size": 74, "upper": True,  "italic": True,  "outline": 4, "shadow": 4, "default_accent": "#FFD66C"},
        "clean-12":     {"font": "DM Sans",        "size": 72, "upper": True,  "italic": False, "outline": 4, "shadow": 3, "default_accent": "#FFFFFF"},
        "clean-13":     {"font": "Creato Display", "size": 68, "upper": False, "italic": False, "outline": 3, "shadow": 3, "default_accent": "#FFFFFF"},
        "clean-14":     {"font": "Apple Garamond", "size": 76, "upper": False, "italic": True,  "outline": 3, "shadow": 3, "default_accent": "#FFDFC4"},
        "clean-9":      {"font": "Creato Display", "size": 62, "upper": False, "italic": False, "outline": 2, "shadow": 2, "default_accent": "#FFFFFF"},
        "clean-10":     {"font": "Creato Display", "size": 64, "upper": False, "italic": False, "outline": 3, "shadow": 3, "default_accent": "#A375FA"},
        "clean-11":     {"font": "Apple Garamond", "size": 74, "upper": False, "italic": True,  "outline": 2, "shadow": 2, "default_accent": "#FFFFFF"},
        "clean-15":     {"font": "Creato Display", "size": 66, "upper": False, "italic": False, "outline": 3, "shadow": 2, "default_accent": "#FFFFFF"},
        "clean-lavish": {"font": "Lavish",         "size": 78, "upper": True,  "italic": False, "outline": 3, "shadow": 2, "default_accent": "#FFFFFF"},
        "clean":        {"font": "Creato Display", "size": 66, "upper": False, "italic": False, "outline": 2, "shadow": 2, "default_accent": "#3EA4F1"},
    }
    cfg = styles_cfg.get(style_id, styles_cfg["classic"])
    scale_f = min(width, height) / 1080.0
    fsize = max(28, int(cfg["size"] * scale_f))
    outline = max(2, int(cfg["outline"] * scale_f))
    shadow = max(1, int(cfg["shadow"] * scale_f))
    pos_x = int(width * 0.5)
    pos_y = int(height * max(12, min(88, float(pos_y_pct))) / 100.0)
    accent_ass = _hex_to_ass_bgr(accent_hex or cfg["default_accent"])
    italic_flag = -1 if cfg["italic"] else 0

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{cfg['font']},{fsize},&H00FFFFFF,&H00FFFFFF,&H000A0E0C,&H80000000,-1,{italic_flag},0,0,100,100,0,0,1,{outline},{shadow},5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in captions:
        words = c.get("words") or []
        if not words:
            continue
        # Pick main emphasized word in the caption
        main_idx = max(range(len(words)), key=lambda i: len(re.sub(r"[^\wà-ú]", "", words[i]["w"])))
        t0 = _fmt_ass_time(c["s"])
        t1 = _fmt_ass_time(c["e"] + 0.08)

        parts = []
        for idx, w in enumerate(words):
            txt = w["w"].upper() if cfg["upper"] else w["w"]
            # Pop-in animation on each word relative to caption start
            rel_ms = max(0, int((w["s"] - c["s"]) * 1000))
            if idx == main_idx:
                parts.append(
                    f"{{\\c{accent_ass}\\fscx108\\fscy108\\t({rel_ms},{rel_ms+140},\\fscx116\\fscy116)}}{txt}{{\\r}}"
                )
            else:
                parts.append(
                    f"{{\\c&H00FFFFFF&\\t({rel_ms},{rel_ms+120},\\fscx103\\fscy103)}}{txt}{{\\r}}"
                )
        line_text = f"{{\\an5\\pos({pos_x},{pos_y})\\fad(70,50)}}" + " ".join(parts)
        events.append(f"Dialogue: 0,{t0},{t1},Default,,0,0,0,,{line_text}")

    Path(out_path).write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def resolve_export_size(src_w, src_h, resolution="1080p"):
    """Compute even target (width, height) preserving portrait/landscape orientation."""
    src_w = max(2, int(src_w or 1080))
    src_h = max(2, int(src_h or 1920))
    portrait = src_h >= src_w
    res = (resolution or "1080p").lower().strip()
    if res == "4k":
        tw, th = (2160, 3840) if portrait else (3840, 2160)
    elif res == "1080p":
        tw, th = (1080, 1920) if portrait else (1920, 1080)
    else:
        tw, th = src_w, src_h
    return tw - (tw % 2), th - (th % 2)


def render_video(src_path, out_path, keep_ranges, ass_path, impact_times, hw, zoom_enabled=True, width=1080, height=1920):
    ffmpeg, _ = find_ffmpeg()
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_escaped = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")

    w_even = width - (width % 2)
    h_even = height - (height % 2)

    # Build trim + concat filter if decupagem cut segments
    n_segs = len(keep_ranges)
    fc_parts = []
    concat_inputs = []
    for i, seg in enumerate(keep_ranges):
        s, e = seg["s"], seg["e"]
        fc_parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]")
        fc_parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]")
        concat_inputs.append(f"[v{i}][a{i}]")

    if n_segs == 1 and keep_ranges[0]["s"] == 0.0:
        v_chain = "[0:v]"
        a_map = "0:a?"
        fc_parts = []
    else:
        fc_parts.append("".join(concat_inputs) + f"concat=n={n_segs}:v=1:a=1[vcat][acat]")
        v_chain = "[vcat]"
        a_map = "[acat]"

    low_ram = hw.get("ram_gb", 8.0) <= 1.2

    # Scale to exact target export resolution (capped to 1080p on 512MB containers to prevent OOM 502)
    if low_ram and max(w_even, h_even) > 1920:
        if h_even >= w_even:
            w_even, h_even = 1080, 1920
        else:
            w_even, h_even = 1920, 1080
    scale_flags = "bilinear" if low_ram else "lanczos"
    scale_base = f"scale={w_even}:{h_even}:force_original_aspect_ratio=decrease:flags={scale_flags},pad={w_even}:{h_even}:(ow-iw)/2:(oh-ih)/2:black,"

    # Smooth ease-in-out zoom pulse on key impact moments (skipped on <=1.2GB RAM to avoid OOM)
    zoom_filter = ""
    if zoom_enabled and impact_times and not low_ram:
        terms = []
        for idx, (imp_s, imp_e) in enumerate(impact_times[:8]):
            dur = max(0.9, min(2.4, (imp_e - imp_s) + 0.7))
            terms.append(f"between(t,{imp_s:.2f},{(imp_s+dur):.2f})*0.12*0.5*(1-cos(2*PI*(t-{imp_s:.2f})/{dur:.2f}))")
        if terms:
            z_expr = "1+" + "+".join(terms)
            zoom_filter = f"scale=w='trunc(iw*({z_expr})/2)*2':h='trunc(ih*({z_expr})/2)*2':eval=frame,crop=w={w_even}:h={h_even},"

    sub_filter = f"{scale_base}{zoom_filter}subtitles='{ass_escaped}':fontsdir='{fonts_escaped}'"
    if fc_parts:
        fc_parts.append(f"{v_chain}{sub_filter}[vout]")
        fc = ";".join(fc_parts)
        map_args = ["-filter_complex", fc, "-map", "[vout]", "-map", a_map]
    else:
        map_args = ["-vf", sub_filter, "-map", "0:v:0", "-map", "0:a?"]

    base_cmd = [ffmpeg, "-y", "-i", str(src_path)] + map_args + [
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"
    ]

    if hw.get("nvenc_ready"):
        nv_cmd = base_cmd + ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "18", str(out_path)]
        r = subprocess.run(nv_cmd, capture_output=True, text=True)
        if r.returncode == 0 and Path(out_path).exists():
            return

    if low_ram:
        cpu_cmd = base_cmd + [
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-rc-lookahead", "10", "-refs", "1", "-bf", "0",
            "-threads", "1", str(out_path)
        ]
    else:
        cpu_preset = "fast" if hw.get("cpu_cores", 4) >= 4 else "veryfast"
        cpu_cmd = base_cmd + [
            "-c:v", "libx264", "-preset", cpu_preset, "-crf", "17",
            "-threads", str(hw.get("cpu_threads", 0)), str(out_path)
        ]
    r = subprocess.run(cpu_cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Erro no FFmpeg: {(r.stderr or '')[-400:]}")
