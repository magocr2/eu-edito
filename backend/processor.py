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

    nvenc_ready = False
    if cuda_ready:
        ffmpeg_exe, _ = find_ffmpeg()
        try:
            r = subprocess.run([ffmpeg_exe, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=4)
            nvenc_ready = "h264_nvenc" in (r.stdout or "")
        except Exception:
            pass

    if cuda_ready:
        model, device, compute, threads, beam = "large-v3-turbo", "cuda", cuda_compute, min(cores, 6), 5
        label = "GPU NVIDIA (CUDA + NVENC)" if nvenc_ready else "GPU NVIDIA (CUDA)"
    elif ram_gb < 0.9:
        model, device, compute, threads, beam = "base", "cpu", "int8", max(1, min(cores, 2)), 4
        label = f"Modo Econômico ({model} · {ram_gb}GB RAM)"
    elif ram_gb < 3.5:
        model, device, compute, threads, beam = "small", "cpu", "int8", max(2, min(cores, 4)), 5
        label = f"Modo Preciso ({model} · {ram_gb}GB RAM)"
    else:
        model, device, compute, threads, beam = "large-v3-turbo", "cpu", "int8", max(2, min(cores, 8)), 5
        label = f"Modo Máxima Precisão ({model} · {threads} threads)"

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
        "-show_streams", "-show_format",
        "-of", "json", str(video_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    data = json.loads(r.stdout or "{}")
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    w = int(stream.get("width") or 1080)
    h = int(stream.get("height") or 1920)
    dur = float(stream.get("duration") or fmt.get("duration") or 0.0)

    # Check display matrix / rotate metadata so vertical iPhone/Android videos stay 9:16
    rot = 0
    try:
        tags = stream.get("tags") or {}
        if "rotate" in tags:
            rot = int(float(tags["rotate"]))
        for sd in (stream.get("side_data_list") or []):
            if "rotation" in sd:
                rot = int(float(sd["rotation"]))
    except Exception:
        rot = 0
    if abs(rot) in (90, 270):
        w, h = h, w

    return {"width": w, "height": h, "duration": dur}


def _transcribe_worker_subprocess(audio_input, model_name, device, compute_type, cpu_threads, beam, language):
    """Run Whisper in an isolated subprocess so OS reclaims 100% of C++ RAM on exit."""
    import sys
    code = (
        "import json, sys; from faster_whisper import WhisperModel; "
        "a, m, d, ct, th, bm, lang = sys.argv[1:8]; "
        "kw = {'device': d, 'compute_type': ct}; "
        "\nif d == 'cpu': kw['cpu_threads'] = int(th)\n"
        "wm = WhisperModel(m, **kw); "
        "segs, info = wm.transcribe(a, language=lang, beam_size=int(bm), temperature=0.0, no_speech_threshold=0.6, vad_filter=False, word_timestamps=True, "
        "condition_on_previous_text=False, repetition_penalty=1.15, no_repeat_ngram_size=3); "
        "words = [{'w': (w.word or '').strip(), 's': round(float(w.start),3), 'e': round(float(w.end),3)} for s in segs for w in (s.words or []) if (w.word or '').strip()]; "
        "print(json.dumps({'words': words, 'duration': float(getattr(info, 'duration', 0.0) or 0.0)}, ensure_ascii=False))"
    )
    res = subprocess.run(
        [sys.executable, "-c", code, str(audio_input), str(model_name), str(device), str(compute_type), str(cpu_threads), str(beam), str(language or "pt")],
        capture_output=True, text=True, timeout=240
    )
    if res.returncode != 0:
        raise RuntimeError(f"Whisper subprocess failed ({res.returncode}): {(res.stderr or '')[-300:]}")
    data = json.loads((res.stdout or "{}").strip().splitlines()[-1])
    return data.get("words", []), float(data.get("duration", 0.0))


def _transcribe_groq(audio_mp3_path, api_key, language="pt"):
    """Call Groq Whisper large-v3-turbo API (free tier, ~1s, 0 MB local RAM) with word timestamps."""
    import mimetypes, urllib.request
    boundary = f"----EuEdito{uuid.uuid4().hex}"
    fields = [
        ("model", "whisper-large-v3-turbo"),
        ("language", language or "pt"),
        ("response_format", "verbose_json"),
        ("temperature", "0"),
        ("timestamp_granularities[]", "word"),
    ]
    body = bytearray()
    for name, val in fields:
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode("utf-8"))
    fname = Path(audio_mp3_path).name
    fdata = Path(audio_mp3_path).read_bytes()
    body.extend(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{fname}\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode("utf-8")
    )
    body.extend(fdata)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=bytes(body),
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "EuEdito/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    words = []
    for w in (res.get("words") or []):
        txt = (w.get("word") or "").strip()
        if txt:
            words.append({"w": txt, "s": round(float(w["start"]), 3), "e": round(float(w["end"]), 3)})
    return words, float(res.get("duration") or 0.0)


def transcribe_video(video_path, hw, language="pt"):
    ffmpeg, _ = find_ffmpeg()
    groq_key = (os.environ.get("GROQ_API_KEY") or "").strip()
    if groq_key:
        mp3_path = Path(video_path).with_suffix(".16k.mp3")
        try:
            subprocess.run(
                [ffmpeg, "-y", "-i", str(video_path), "-vn", "-af", "highpass=f=80,loudnorm=I=-16:TP=-1.5", "-ac", "1", "-ar", "16000", "-b:a", "48k", str(mp3_path)],
                capture_output=True, timeout=120
            )
            if mp3_path.exists() and mp3_path.stat().st_size > 1000:
                return _transcribe_groq(mp3_path, groq_key, language=language)
        except Exception as e:
            print("Groq fallback to local Whisper:", e)
        finally:
            try:
                mp3_path.unlink(missing_ok=True)
            except Exception:
                pass

    # Extract clean, volume-normalized 16kHz mono WAV so quiet phone speech is crystal clear
    wav_path = Path(video_path).with_suffix(".16k.wav")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(video_path), "-vn", "-af", "highpass=f=80,loudnorm=I=-16:TP=-1.5", "-ac", "1", "-ar", "16000", "-f", "wav", str(wav_path)],
            capture_output=True, timeout=120
        )
    except Exception:
        pass
    audio_input = str(wav_path) if (wav_path.exists() and wav_path.stat().st_size > 1000) else str(video_path)

    try:
        if hw.get("ram_gb", 8.0) <= 1.2:
            # Isolated subprocess guarantees 100% C++ memory release before FFmpeg runs
            return _transcribe_worker_subprocess(
                audio_input, hw["whisper_model"], hw["device"], hw["compute_type"],
                hw["cpu_threads"], hw["beam_size"], language
            )

        model, beam = _get_whisper_model(hw)
        segments, info = model.transcribe(
            audio_input,
            language=language or "pt",
            beam_size=beam,
            temperature=0.0,
            no_speech_threshold=0.6,
            vad_filter=False,
            word_timestamps=True,
            condition_on_previous_text=False,
            repetition_penalty=1.15,
            no_repeat_ngram_size=3,
        )
        words = []
        for seg in segments:
            for w in (seg.words or []):
                txt = (w.word or "").strip()
                if txt:
                    words.append({"w": txt, "s": round(float(w.start), 3), "e": round(float(w.end), 3)})
        return words, float(getattr(info, "duration", 0.0) or 0.0)
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except Exception:
            pass


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
        mapped_words.append({"w": w["w"], "s": round(ms, 3), "e": round(me, 3), "orig_s": round(w["s"], 3), "orig_e": round(w["e"], 3)})

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
                "orig_s": cur[0]["orig_s"],
                "orig_e": cur[-1]["orig_e"],
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
            "orig_s": cur[0]["orig_s"],
            "orig_e": cur[-1]["orig_e"],
            "text": " ".join(x["w"] for x in cur),
            "words": cur,
        })
    return captions


def apply_manual_caption_cuts(keep_ranges, edited_captions):
    """Subtract manually cut caption intervals from keep_ranges and remap kept captions."""
    cut_spans = []
    kept_caps = []
    for c in (edited_captions or []):
        if c.get("cut"):
            os_t = float(c.get("orig_s", c.get("s", 0.0)))
            oe_t = float(c.get("orig_e", c.get("e", os_t + 0.3)))
            cut_spans.append((max(0.0, os_t - 0.04), oe_t + 0.04))
        else:
            kept_caps.append(c)

    if not cut_spans:
        return keep_ranges, kept_caps

    new_keep = []
    for seg in keep_ranges:
        pieces = [(float(seg["s"]), float(seg["e"]))]
        for cs, ce in cut_spans:
            next_pieces = []
            for ps, pe in pieces:
                if ce <= ps or cs >= pe:
                    next_pieces.append((ps, pe))
                else:
                    if cs - ps >= 0.15:
                        next_pieces.append((ps, cs))
                    if pe - ce >= 0.15:
                        next_pieces.append((ce, pe))
            pieces = next_pieces
        for ps, pe in pieces:
            new_keep.append({"s": round(ps, 3), "e": round(pe, 3)})

    if not new_keep:
        new_keep = keep_ranges

    # Remap kept captions onto updated timeline using their original timestamps
    remapped = []
    for c in kept_caps:
        os_t = float(c.get("orig_s", c.get("s", 0.0)))
        oe_t = float(c.get("orig_e", c.get("e", os_t + 0.4)))
        ns = map_time_to_edited(os_t, new_keep)
        ne = max(ns + 0.15, map_time_to_edited(oe_t, new_keep))
        c_copy = dict(c)
        c_copy["s"] = round(ns, 3)
        c_copy["e"] = round(ne, 3)
        remapped_words = []
        for w in (c.get("words") or []):
            wos = float(w.get("orig_s", w.get("s", os_t)))
            woe = float(w.get("orig_e", w.get("e", wos + 0.15)))
            wns = map_time_to_edited(wos, new_keep)
            wne = max(wns + 0.08, map_time_to_edited(woe, new_keep))
            remapped_words.append({"w": w["w"], "s": round(wns, 3), "e": round(wne, 3), "orig_s": round(wos, 3), "orig_e": round(woe, 3)})
        c_copy["words"] = remapped_words
        remapped.append(c_copy)
    return new_keep, remapped


def sync_edited_captions(edited_captions):
    """Ensure edited caption texts have valid word-level timestamps for ASS rendering."""
    synced = []
    for cap in (edited_captions or []):
        text = (cap.get("text") or "").strip()
        if not text:
            continue
        s = float(cap.get("s", 0.0))
        e = max(s + 0.15, float(cap.get("e", s + 0.5)))
        orig_words = cap.get("words") or []
        new_tokens = text.split()
        if len(new_tokens) == len(orig_words) and orig_words:
            words = [
                {"w": tok, "s": float(orig_words[i]["s"]), "e": float(orig_words[i]["e"])}
                for i, tok in enumerate(new_tokens)
            ]
        else:
            step = (e - s) / max(1, len(new_tokens))
            words = [
                {"w": tok, "s": round(s + i * step, 3), "e": round(s + (i + 1) * step, 3)}
                for i, tok in enumerate(new_tokens)
            ]
        synced.append({"s": round(s, 3), "e": round(e, 3), "text": text, "words": words})
    return synced


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




def generate_ass(captions, out_path, width=1080, height=1920, style_id="classic", accent_hex="", pos_y_pct=74, caption_lines=3, caption_scale=100, hook_title="", hook_style="pill-white", hook_y_pct=16):
    """
    Generate CapCut-grade ASS subtitles matching the 11 web preview models 1-to-1:
    - True ASS alpha (&HC4000000& subtle anti-alias edge, &H5C000000& soft shadow — zero black box or heavy stroke)
    - Soft neon/bloom glow layer behind accent highlight words
    - Mode 1 (1 linha): single unified libass Dialogue line (perfect spacing & dead-center alignment)
    - Mode 2 (2 linhas): strictly <= 2 balanced rows without orphan words
    - Mode 3 (2 ou 3 linhas): smart adaptive 2-or-3 staggered editorial rows (before top-left, MAIN center, after bottom-right)
      with visually equal top/bottom spacing around uppercase MAIN words
    """
    styles_cfg = {
        "classic": {
            "small_font": "Creato Display", "small_file": "CreatoDisplay-Regular.otf", "small_size": 52, "small_bold": 0, "small_italic": 0,
            "main_font": "Creato Display", "main_file": "CreatoDisplay-ExtraBold.otf", "main_size": 102, "main_bold": -1, "main_italic": 0,
            "upper": True, "default_accent": "#FFFFFF", "anim": "rise",
        },
        "model-07": {
            "small_font": "Geist", "small_file": "Geist.ttf", "small_size": 50, "small_bold": 0, "small_italic": 0,
            "main_font": "Apple Garamond", "main_file": "AppleGaramond-BoldItalic.ttf", "main_size": 110, "main_bold": -1, "main_italic": -1,
            "upper": True, "default_accent": "#FFD66C", "anim": "pop",
        },
        "clean-12": {
            "small_font": "DM Sans 9pt", "small_file": "DMSans.ttf", "small_size": 50, "small_bold": 0, "small_italic": 0,
            "main_font": "DM Sans 9pt", "main_file": "DMSans.ttf", "main_size": 98, "main_bold": -1, "main_italic": 0,
            "upper": True, "default_accent": "#FFFFFF", "anim": "pop",
        },
        "clean-13": {
            "small_font": "Apple Garamond", "small_file": "AppleGaramond-Italic.ttf", "small_size": 52, "small_bold": 0, "small_italic": -1,
            "main_font": "Creato Display Medium", "main_file": "CreatoDisplay-Medium.otf", "main_size": 96, "main_bold": 0, "main_italic": 0,
            "upper": True, "default_accent": "#FFFFFF", "anim": "slide",
        },
        "clean-14": {
            "small_font": "Creato Display", "small_file": "CreatoDisplay-Regular.otf", "small_size": 52, "small_bold": 0, "small_italic": 0,
            "main_font": "Apple Garamond", "main_file": "AppleGaramond-Italic.ttf", "main_size": 112, "main_bold": 0, "main_italic": -1,
            "upper": False, "default_accent": "#FFDFC4", "anim": "pop",
        },
        "clean-9": {
            "small_font": "Creato Display Light", "small_file": "CreatoDisplay-Light.otf", "small_size": 48, "small_bold": 0, "small_italic": 0,
            "main_font": "Creato Display", "main_file": "CreatoDisplay-Regular.otf", "main_size": 92, "main_bold": 0, "main_italic": 0,
            "upper": False, "default_accent": "#FFFFFF", "anim": "blur",
        },
        "clean-10": {
            "small_font": "Creato Display", "small_file": "CreatoDisplay-Regular.otf", "small_size": 48, "small_bold": 0, "small_italic": 0,
            "main_font": "Creato Display", "main_file": "CreatoDisplay-Bold.otf", "main_size": 60, "main_bold": -1, "main_italic": 0,
            "upper": False, "default_accent": "#A375FA", "anim": "rise",
        },
        "clean-11": {
            "small_font": "Creato Display Light", "small_file": "CreatoDisplay-Light.otf", "small_size": 48, "small_bold": 0, "small_italic": 0,
            "main_font": "Apple Garamond", "main_file": "AppleGaramond-Italic.ttf", "main_size": 110, "main_bold": 0, "main_italic": -1,
            "upper": False, "default_accent": "#FFFFFF", "anim": "cut",
        },
        "clean-15": {
            "small_font": "Creato Display", "small_file": "CreatoDisplay-Regular.otf", "small_size": 50, "small_bold": 0, "small_italic": 0,
            "main_font": "Creato Display", "main_file": "CreatoDisplay-Bold.otf", "main_size": 94, "main_bold": -1, "main_italic": 0,
            "upper": False, "default_accent": "#FFFFFF", "anim": "rise",
        },
        "clean-lavish": {
            "small_font": "Lavish", "small_file": "lavish.otf", "small_size": 52, "small_bold": 0, "small_italic": 0,
            "main_font": "Lavish", "main_file": "lavish.otf", "main_size": 104, "main_bold": 0, "main_italic": 0,
            "upper": True, "default_accent": "#FFFFFF", "anim": "slide",
        },
        "clean": {
            "small_font": "Apple Garamond", "small_file": "AppleGaramond-Italic.ttf", "small_size": 50, "small_bold": 0, "small_italic": -1,
            "main_font": "Creato Display Medium", "main_file": "CreatoDisplay-Medium.otf", "main_size": 94, "main_bold": 0, "main_italic": 0,
            "upper": False, "default_accent": "#FFFFFF", "anim": "slide",
        },
    }
    cfg = styles_cfg.get(style_id, styles_cfg["classic"])
    scale_f = min(width, height) / 1080.0
    user_scale = max(0.60, min(1.45, float(caption_scale or 100) / 100.0))
    s_size = max(20, int(cfg["small_size"] * scale_f * user_scale))
    m_size = max(28, int(cfg["main_size"] * scale_f * user_scale))
    outline = round(max(0.7, 1.0 * scale_f), 1)
    shadow = round(max(2.2, 3.6 * scale_f), 1)
    pos_x = int(width * 0.5)
    pos_y = int(height * max(16, min(84, float(pos_y_pct))) / 100.0)
    chosen_hex = (accent_hex or "").strip() or cfg["default_accent"]
    accent_ass = _hex_to_ass_bgr(chosen_hex)
    glow_blur = round(max(6.0, 12.0 * scale_f), 1)
    glow_bord = round(max(2.0, 3.5 * scale_f), 1)
    has_color_accent = chosen_hex.upper() not in ("#FFFFFF", "FFFFFF")
    glow_alpha = "&H92&" if has_color_accent else "&HB6&"

    # True ASS alpha: FF=transparent, 00=opaque! &HC4000000& = subtle edge, &H5C000000& = soft diffused drop shadow
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Small,{cfg['small_font']},{s_size},&H00FFFFFF,&H00FFFFFF,&HC4000000,&H5C000000,{cfg['small_bold']},{cfg['small_italic']},0,0,100,100,0,0,1,{outline},{shadow},5,36,36,36,1
Style: Main,{cfg['main_font']},{m_size},{accent_ass},{accent_ass},&HC4000000,&H5C000000,{cfg['main_bold']},{cfg['main_italic']},0,0,100,100,0,0,1,{outline},{round(shadow * 1.15, 1)},5,36,36,36,1
Style: MainGlow,{cfg['main_font']},{m_size},{accent_ass},{accent_ass},{accent_ass},&HFF000000,{cfg['main_bold']},{cfg['main_italic']},0,0,100,100,0,0,1,{glow_bord},0,5,36,36,36,1
Style: HookBox,Creato Display,{max(26, int(44 * scale_f))},&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,{max(10, int(16 * scale_f))},0,5,40,40,40,1
Style: HookDark,Creato Display,{max(26, int(44 * scale_f))},&H00FFFFFF,&H00FFFFFF,&HCC0A120D,&HCC0A120D,-1,0,0,0,100,100,0,0,3,{max(10, int(16 * scale_f))},0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    req_lines = int(caption_lines or 3)
    if style_id == "clean-10":
        req_lines = 1
    anim = cfg["anim"]

    # Load Pillow ImageFont if available for exact pixel width measurement & cap clamping
    s_pil = m_pil = None
    try:
        from PIL import ImageFont
        s_fp = FONTS_DIR / cfg["small_file"]
        m_fp = FONTS_DIR / cfg["main_file"]
        if s_fp.exists():
            s_pil = ImageFont.truetype(str(s_fp), s_size)
        if m_fp.exists():
            m_pil = ImageFont.truetype(str(m_fp), m_size)
    except Exception:
        s_pil = m_pil = None

    def _measure(txt, is_main=False, custom_sz=None):
        font_obj = m_pil if is_main else s_pil
        sz = custom_sz or (m_size if is_main else s_size)
        if font_obj is not None:
            try:
                base_sz = m_size if is_main else s_size
                return float(font_obj.getlength(txt)) * (sz / max(base_sz, 1))
            except Exception:
                pass
        return len(txt) * sz * 0.50

    def _word_score(w):
        clean = re.sub(r"[^\w\u00e0-\u00fa\u00c0-\u00da]", "", w["w"])
        sc = len(clean)
        if clean.lower() in _IMPACT_WORDS:
            sc += 12
        return sc

    def _word_reveal(rel_ms, is_glow=False):
        t0 = max(0, int(rel_ms))
        dur = 25 if anim == "cut" else (190 if anim == "blur" else 135)
        if is_glow:
            return f"\\alpha&HFF&\\t({t0},{t0 + dur},\\1a{glow_alpha}\\3a&HCE&\\4a&HFF&)"
        return f"\\alpha&HFF&\\t({t0},{t0 + dur},\\1a&H00&\\3a&HC4&\\4a&H5C&)"

    def _entry_motion(x, y, is_main=False, target_scale=100, is_glow=False):
        d = int(14 * scale_f)
        if anim == "rise":
            return f"\\move({x},{y + d},{x},{y},0,220)"
        if anim == "slide":
            return f"\\move({x + int(d * 1.2)},{y},{x},{y},0,220)"
        if anim == "blur":
            end_blur = glow_blur if is_glow else 1.1
            return f"\\move({x},{y - int(d * 0.6)},{x},{y},0,210)\\blur{round(end_blur + 3.5, 1)}\\t(0,220,\\blur{end_blur})"
        if anim == "pop" and is_main:
            s_lo = max(50, int(target_scale * 0.78))
            s_hi = int(target_scale * 1.05)
            return f"\\pos({x},{y})\\fscx{s_lo}\\fscy{s_lo}\\t(0,150,\\fscx{s_hi}\\fscy{s_hi})\\t(150,240,\\fscx{target_scale}\\fscy{target_scale})"
        return f"\\pos({x},{y})"

    def _inline_switch(is_main_tok, is_glow=False, main_sz_override=None):
        """Return inline ASS override tag for switching between Small and Main styles inside one line."""
        if is_glow:
            if not is_main_tok:
                return f"\\fn{cfg['small_font']}\\fs{s_size}\\b{cfg['small_bold']}\\i{cfg['small_italic']}\\alpha&HFF&"
            msz = main_sz_override or m_size
            return (
                f"\\fn{cfg['main_font']}\\fs{msz}\\b{cfg['main_bold']}\\i{cfg['main_italic']}"
                f"\\1c{accent_ass}\\3c{accent_ass}\\4c&HFF000000&\\bord{glow_bord}\\shad0\\blur{glow_blur}"
            )
        if is_main_tok:
            msz = main_sz_override or m_size
            return (
                f"\\fn{cfg['main_font']}\\fs{msz}\\b{cfg['main_bold']}\\i{cfg['main_italic']}"
                f"\\1c{accent_ass}\\3c&HC4000000&\\4c&H5C000000&\\bord{outline}\\shad{round(shadow * 1.15, 1)}\\blur1.0"
            )
        return (
            f"\\fn{cfg['small_font']}\\fs{s_size}\\b{cfg['small_bold']}\\i{cfg['small_italic']}"
            f"\\1c&H00FFFFFF&\\3c&HC4000000&\\4c&H5C000000&\\bord{outline}\\shad{shadow}\\blur1.0"
        )

    def _emit_mixed_line(tokens, x_center, y_row, cap_s, t0s, t1s, main_local_idx=None, inline_main_scale=1.0):
        """Render a single horizontal ASS line (Small or mixed Small+Main) centered natively by libass."""
        if not tokens:
            return
        max_w = width * 0.86
        inline_m_sz = max(s_size + 4, int(m_size * inline_main_scale)) if main_local_idx is not None else m_size
        est_w = 0.0
        for idx, w in enumerate(tokens):
            is_m = (main_local_idx is not None and idx == main_local_idx)
            txt = w["w"].upper() if (is_m and cfg["upper"]) else w["w"]
            est_w += _measure(txt, is_main=is_m, custom_sz=(inline_m_sz if is_m else s_size))
        est_w += _measure(" ", is_main=False) * max(0, len(tokens) - 1)
        fit_pct = min(100, max(54, int((max_w / max(est_w, 1.0)) * 100)))
        half_w = (est_w * (fit_pct / 100.0)) / 2.0
        safe_x = int(max(width * 0.07 + half_w, min(width * 0.93 - half_w, x_center)))
        if half_w * 2 > width * 0.82:
            safe_x = pos_x

        scale_tag = f"\\fscx{fit_pct}\\fscy{fit_pct}" if fit_pct < 100 else ""
        has_main = (main_local_idx is not None and 0 <= main_local_idx < len(tokens))

        # Layer 1: Soft Glow halo behind any Main highlight token on this line
        if has_main:
            solo_main_glow = (len(tokens) == 1)
            glow_motion = _entry_motion(safe_x, y_row, is_main=solo_main_glow, target_scale=fit_pct, is_glow=True)
            glow_scale = "" if (solo_main_glow and anim == "pop") else scale_tag
            glow_blur_tag = f"\\blur{glow_blur}" if anim != "blur" else ""
            g_chunks = []
            for idx, w in enumerate(tokens):
                is_m = (idx == main_local_idx)
                txt = w["w"].upper() if (is_m and cfg["upper"]) else w["w"]
                if is_m:
                    rel_ms = max(0, (float(w["s"]) - cap_s) * 1000)
                    sw = _inline_switch(True, is_glow=True, main_sz_override=inline_m_sz)
                    g_chunks.append(f"{{{sw}{_word_reveal(rel_ms, is_glow=True)}}}{txt}")
                else:
                    sw = _inline_switch(False, is_glow=True, main_sz_override=inline_m_sz)
                    g_chunks.append(f"{{{sw}}}{txt}")
            # IMPORTANT: use Small as base style when mixed so space glyphs match foreground 100% identically
            glow_base_style = "MainGlow" if solo_main_glow else "Small"
            # Separate trailing words back into Small before spacing so inter-word spaces never use Main metrics
            glow_text = f" {{{_inline_switch(False, is_glow=True)}}}".join(g_chunks) if not solo_main_glow else g_chunks[0]
            events.append(
                f"Dialogue: 1,{t0s},{t1s},{glow_base_style},,0,0,0,,{{\\an5{glow_motion}{glow_scale}{glow_blur_tag}}}{glow_text}"
            )

        # Layer 2 (Main) or Layer 0 (Small): Crisp centered foreground text
        solo_main = (has_main and len(tokens) == 1)
        motion = _entry_motion(safe_x, y_row, is_main=solo_main, target_scale=fit_pct, is_glow=False)
        fg_scale = "" if (solo_main and anim == "pop") else scale_tag
        blur_base = "\\blur1.0" if anim != "blur" else ""
        fg_chunks = []
        for idx, w in enumerate(tokens):
            is_m = (has_main and idx == main_local_idx)
            txt = w["w"].upper() if (is_m and cfg["upper"]) else w["w"]
            rel_ms = max(0, (float(w["s"]) - cap_s) * 1000)
            rev = _word_reveal(rel_ms, is_glow=False)
            if has_main and not solo_main:
                sw = _inline_switch(is_m, is_glow=False, main_sz_override=inline_m_sz)
                fg_chunks.append(f"{{{sw}{rev}}}{txt}")
            else:
                fg_chunks.append(f"{{{rev}}}{txt}")

        style_name = "Main" if solo_main else "Small"
        layer_id = 2 if has_main else 0
        if has_main and not solo_main:
            fg_text = f" {{{_inline_switch(False, is_glow=False)}}}".join(fg_chunks)
        else:
            fg_text = " ".join(fg_chunks)
        events.append(
            f"Dialogue: {layer_id},{t0s},{t1s},{style_name},,0,0,0,,{{\\an5{motion}{fg_scale}{blur_base}}}{fg_text}"
        )

    for c in captions:
        words = c.get("words") or []
        text = (c.get("text") or "").strip() or " ".join(w.get("w", "") for w in words).strip()
        if not text:
            continue
        cap_s = float(c["s"])
        cap_e = float(c["e"])
        if not words:
            toks = text.split()
            step = max(0.08, (cap_e - cap_s) / max(1, len(toks)))
            words = [{"w": tok, "s": cap_s + i * step, "e": cap_s + (i + 1) * step} for i, tok in enumerate(toks)]

        t0s = _fmt_ass_time(cap_s)
        t1s = _fmt_ass_time(cap_e + 0.12)
        main_idx = max(range(len(words)), key=lambda i: _word_score(words[i]))

        # --- MODE 1: Single Unified Line (natural spacing, 100% centered) ---
        if req_lines == 1 or len(words) == 1:
            _emit_mixed_line(words, pos_x, pos_y, cap_s, t0s, t1s, main_local_idx=main_idx, inline_main_scale=0.86)
            continue

        before = words[:main_idx]
        main_w = [words[main_idx]]
        after = words[main_idx + 1:]

        # Decide cleanly between 2 rows vs 3 staggered editorial rows
        use_three = False
        if req_lines >= 3 and before and after:
            before_chars = sum(len(x["w"]) for x in before)
            after_chars = sum(len(x["w"]) for x in after)
            # Avoid weak 1-short-word orphans (e.g. "tem", "que", "de") alone on row 3
            if len(words) >= 4 and (len(before) >= 2 or before_chars >= 6) and (len(after) >= 2 or after_chars >= 5):
                use_three = True

        # Visual baseline offsets: keep top & bottom whitespace symmetric when MAIN is uppercase
        upper_main = cfg["upper"]
        top_offset = int(m_size * 0.54 + s_size * 0.14)
        bot_offset = int(m_size * (0.34 if upper_main else 0.42) + s_size * 0.21)
        main_txt = main_w[0]["w"].upper() if upper_main else main_w[0]["w"]
        main_w_px = min(width * 0.78, _measure(main_txt, is_main=True))
        stag = min(int(width * 0.13), max(int(width * 0.04), int(main_w_px * 0.18)))

        if use_three:
            # Subtle editorial diagonal stagger only on 3-line balanced phrases
            _emit_mixed_line(before, pos_x - stag, pos_y - top_offset, cap_s, t0s, t1s, main_local_idx=None)
            _emit_mixed_line(main_w, pos_x, pos_y, cap_s, t0s, t1s, main_local_idx=0, inline_main_scale=1.0)
            _emit_mixed_line(after, pos_x + stag, pos_y + bot_offset, cap_s, t0s, t1s, main_local_idx=None)
        elif before and after:
            # Strictly 2 centered balanced rows when MAIN is in the middle
            before_chars = sum(len(x["w"]) for x in before)
            after_chars = sum(len(x["w"]) for x in after)
            row_gap_up = int(m_size * 0.46 + s_size * 0.14)
            row_gap_dn = int(m_size * (0.20 if upper_main else 0.26))
            if after_chars <= before_chars:
                _emit_mixed_line(before, pos_x, pos_y - row_gap_up, cap_s, t0s, t1s, main_local_idx=None)
                _emit_mixed_line(main_w + after, pos_x, pos_y + row_gap_dn, cap_s, t0s, t1s, main_local_idx=0, inline_main_scale=0.86)
            else:
                _emit_mixed_line(before + main_w, pos_x, pos_y - row_gap_up, cap_s, t0s, t1s, main_local_idx=len(before), inline_main_scale=0.86)
                _emit_mixed_line(after, pos_x, pos_y + row_gap_dn + int(s_size * 0.24), cap_s, t0s, t1s, main_local_idx=None)
        elif before:
            # 2 lines cleanly centered: small before on top, MAIN below
            top_2 = int(m_size * 0.42 + s_size * 0.14)
            bot_2 = int(m_size * 0.18)
            _emit_mixed_line(before, pos_x, pos_y - top_2, cap_s, t0s, t1s, main_local_idx=None)
            _emit_mixed_line(main_w, pos_x, pos_y + bot_2, cap_s, t0s, t1s, main_local_idx=0, inline_main_scale=1.0)
        else:
            # 2 lines cleanly centered: MAIN on top, small after below
            top_2 = int(m_size * 0.14)
            bot_2 = int(m_size * (0.34 if upper_main else 0.42) + s_size * 0.18)
            _emit_mixed_line(main_w, pos_x, pos_y - top_2, cap_s, t0s, t1s, main_local_idx=0, inline_main_scale=1.0)
            _emit_mixed_line(after, pos_x, pos_y + bot_2, cap_s, t0s, t1s, main_local_idx=None)

    # Hook overlay
    hook = (hook_title or "").strip()
    if hook:
        hy = int(height * max(8, min(55, float(hook_y_pct or 16))) / 100.0)
        h_st = (hook_style or "pill-white").strip()
        if h_st == "pill-accent":
            events.append(
                f"Dialogue: 2,0:00:00.00,0:00:03.50,HookBox,,0,0,0,,{{\\an5\\pos({pos_x},{hy})\\c&H0008140C&\\3c{accent_ass}\\4c{accent_ass}\\fad(120,200)}}{hook}"
            )
        elif h_st == "glass-dark":
            events.append(
                f"Dialogue: 2,0:00:00.00,0:00:03.50,HookDark,,0,0,0,,{{\\an5\\pos({pos_x},{hy})\\fad(120,200)}}{hook}"
            )
        elif h_st == "clean-shadow":
            hsize = max(28, int(48 * scale_f))
            events.append(
                f"Dialogue: 2,0:00:00.00,0:00:03.50,Main,,0,0,0,,{{\\an5\\pos({pos_x},{hy})\\fs{hsize}\\c&H00FFFFFF&\\3c&HB8000000&\\4c&H5C000000&\\bord1\\shad3\\blur1.4\\fad(120,200)}}{hook}"
            )
        else:
            events.append(
                f"Dialogue: 2,0:00:00.00,0:00:03.50,HookBox,,0,0,0,,{{\\an5\\pos({pos_x},{hy})\\fad(120,200)}}{hook}"
            )

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
    elif res == "720p":
        tw, th = (720, 1280) if portrait else (1280, 720)
    else:
        tw, th = src_w, src_h
    return tw - (tw % 2), th - (th % 2)


def render_video(src_path, out_path, keep_ranges, ass_path, impact_times, hw, zoom_enabled=True, width=1080, height=1920, studio_audio=False):
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

    # Cap export resolution to 720p on 512MB containers to prevent OOM 502 during x264+libass
    if low_ram and max(w_even, h_even) > 1280:
        if h_even >= w_even:
            w_even, h_even = 720, 1280
        else:
            w_even, h_even = 1280, 720
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
    af_chain = "highpass=f=85,afftdn=nf=-22,acompressor=threshold=-18dB:ratio=3:attack=5:release=80,loudnorm=I=-14:TP=-1.5:LRA=11" if studio_audio else ""
    if fc_parts:
        fc_parts.append(f"{v_chain}{sub_filter}[vout]")
        if af_chain:
            fc_parts.append(f"{a_map}{af_chain}[aout]")
            a_map = "[aout]"
        fc = ";".join(fc_parts)
        map_args = ["-filter_complex", fc, "-map", "[vout]", "-map", a_map]
    else:
        map_args = ["-vf", sub_filter] + (["-af", af_chain] if af_chain else []) + ["-map", "0:v:0", "-map", "0:a?"]

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
