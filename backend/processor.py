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

from compositor import (
    IMG_EXTS,
    build_editorial_card_png,
    emit_ass_graphic_fx,
    ensure_rounded_mask,
    ensure_split_mask,
    motion_overlay_expr,
)
from library_catalog import resolve_caption_model

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

    if os.name != "nt":
        # Respect Railway / Render container limits even when host /proc/meminfo looks larger
        if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RENDER"):
            ram_gb = min(ram_gb, 1.0)
        try:
            env_mb = float(os.environ.get("RAILWAY_MEMORY_LIMIT_MB") or 0)
            if env_mb > 64:
                ram_gb = min(ram_gb, round(env_mb / 1024.0, 2))
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

    acmd = [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "json", str(video_path)]
    ar = subprocess.run(acmd, capture_output=True, text=True, timeout=10)
    has_audio = bool(json.loads(ar.stdout or "{}").get("streams"))

    return {"width": w, "height": h, "duration": dur, "has_audio": has_audio}


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


_NO_ORPHAN_END = {
    "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
    "a", "o", "as", "os", "e", "ou", "que", "se", "com", "por", "para", "pra", "um", "uma",
}


def build_captions(words, keep_ranges, max_chars=26):
    """Group words into natural, readable blocks factoring punctuation, speech rate, pauses, and connector words."""
    mapped_words = []
    for w in words:
        mid = (w["s"] + w["e"]) / 2.0
        if not any(seg["s"] - 0.03 <= mid <= seg["e"] + 0.03 for seg in keep_ranges):
            continue
        ms = map_time_to_edited(w["s"], keep_ranges)
        me = map_time_to_edited(w["e"], keep_ranges)
        if me <= ms:
            me = ms + 0.12
        mapped_words.append({
            "w": w["w"],
            "s": round(ms, 3),
            "e": round(me, 3),
            "orig_s": round(w["s"], 3),
            "orig_e": round(w["e"], 3),
        })

    captions = []
    cur = []
    cur_len = 0
    for idx, w in enumerate(mapped_words):
        wlen = len(w["w"])
        gap = (w["s"] - cur[-1]["e"]) if cur else 0.0
        cur_dur = (cur[-1]["e"] - cur[0]["s"]) if cur else 0.0
        prev_clean = re.sub(r"[^\w\u00e0-\u00fa]", "", cur[-1]["w"].lower()) if cur else ""
        has_punct = bool(cur and cur[-1]["w"].endswith((".", "!", "?", ";")))
        soft_comma = bool(cur and cur[-1]["w"].endswith(",") and (cur_len >= 12 or len(cur) >= 3))
        too_long_time = bool(cur and cur_dur >= 2.2 and len(cur) >= 3)
        word_cap = 5 if (cur and cur_len + 1 + wlen <= max_chars - 2 and gap < 0.25) else 4

        should_break = False
        if cur:
            if has_punct or soft_comma or gap > 0.42 or too_long_time:
                should_break = True
            elif len(cur) >= word_cap or (cur_len + 1 + wlen > max_chars):
                # Avoid cutting right after a weak connector word if the next word fits safely
                if prev_clean in _NO_ORPHAN_END and cur_len + 1 + wlen <= max_chars + 5 and gap < 0.30 and len(cur) < 6:
                    should_break = False
                else:
                    should_break = True

        if cur and should_break:
            # Move dangling connector forward to next block when safe and cur keeps >=2 words
            carry = None
            if not has_punct and not soft_comma and gap < 0.28 and len(cur) >= 3 and prev_clean in _NO_ORPHAN_END:
                carry = cur.pop()
            captions.append({
                "s": cur[0]["s"],
                "e": cur[-1]["e"],
                "orig_s": cur[0]["orig_s"],
                "orig_e": cur[-1]["orig_e"],
                "text": " ".join(x["w"] for x in cur),
                "words": cur,
            })
            cur = [carry] if carry else []
            cur_len = len(carry["w"]) if carry else 0
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

    # Avoid single-word dangling blocks when they belong with neighbor
    merged = []
    for cap in captions:
        if merged and len(cap["words"]) == 1 and (cap["s"] - merged[-1]["e"]) <= 0.55:
            prev = merged[-1]
            if len(prev["words"]) <= 3 and len(prev["text"]) + 1 + len(cap["text"]) <= max_chars + 7:
                prev["words"].extend(cap["words"])
                prev["e"] = cap["e"]
                prev["orig_e"] = cap["orig_e"]
                prev["text"] = " ".join(x["w"] for x in prev["words"])
                continue
            elif len(prev["words"]) >= 3:
                w2_clean = re.sub(r"[^\w\u00e0-\u00fa]", "", prev["words"][-2]["w"].lower())
                take_cnt = 2 if (w2_clean in _NO_ORPHAN_END and len(prev["words"]) >= 3) else 1
                stolen_list = [prev["words"].pop() for _ in range(take_cnt)][::-1]
                prev["e"] = prev["words"][-1]["e"]
                prev["orig_e"] = prev["words"][-1]["orig_e"]
                prev["text"] = " ".join(x["w"] for x in prev["words"])
                cap["words"] = stolen_list + cap["words"]
                cap["s"] = stolen_list[0]["s"]
                cap["orig_s"] = stolen_list[0]["orig_s"]
                cap["text"] = " ".join(x["w"] for x in cap["words"])
        merged.append(cap)
    return merged


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
        raw_clean = text.replace("|", " ").replace("\n", " ")
        new_tokens = raw_clean.split()
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
        item = {"s": round(s, 3), "e": round(e, 3), "text": text, "words": words}
        if cap.get("main_indices"):
            valid_mi = [int(x) for x in cap["main_indices"] if 0 <= int(x) < len(words)]
            if valid_mi:
                item["main_indices"] = valid_mi
                item["main_idx"] = valid_mi[0]
        if cap.get("main_idx") is not None and "main_idx" not in item:
            try:
                mi = int(cap["main_idx"])
                if 0 <= mi < len(words):
                    item["main_idx"] = mi
            except Exception:
                pass
        if cap.get("graphic_fx"):
            item["graphic_fx"] = str(cap["graphic_fx"])
        if cap.get("fullscreen"):
            item["fullscreen"] = True
        if "sfx" in cap and cap["sfx"] is not None:
            item["sfx"] = cap["sfx"] if isinstance(cap["sfx"], str) else bool(cap["sfx"])
        if cap.get("broll"):
            item["broll"] = True
        if cap.get("broll_id"):
            item["broll_id"] = str(cap["broll_id"])
        if cap.get("card"):
            item["card"] = True
        if cap.get("card_ids"):
            item["card_ids"] = [str(x) for x in cap["card_ids"]]
        synced.append(item)
    return synced


def _ensure_bokeh_mask(mask_path, w, h, strength=0.65):
    """Generate a smooth radial alpha mask PNG for optical bokeh (center sharp, edges blurred)."""
    from PIL import Image, ImageFilter

    p = Path(mask_path)
    if p.exists() and p.stat().st_size > 500:
        return p
    # Build small gradient mask then upscale smoothly for fast generation
    mw, mh = max(64, w // 8), max(64, h // 8)
    mask = Image.new("L", (mw, mh), 0)
    px = mask.load()
    cx, cy = mw * 0.5, mh * 0.44
    rx, ry = mw * 0.40, mh * 0.34
    max_alpha = int(255 * max(0.2, min(0.85, strength)))
    for y in range(mh):
        dy = (y - cy) / max(ry, 1.0)
        for x in range(mw):
            dx = (x - cx) / max(rx, 1.0)
            d = (dx * dx + dy * dy) ** 0.5
            if d <= 0.65:
                a = 0
            elif d >= 1.35:
                a = max_alpha
            else:
                t = (d - 0.65) / 0.70
                t = t * t * (3.0 - 2.0 * t)
                a = int(max_alpha * t)
            px[x, y] = a
    mask = mask.resize((w, h), Image.Resampling.BILINEAR).filter(ImageFilter.GaussianBlur(4))
    rgba = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    rgba.putalpha(mask)
    rgba.save(str(p), "PNG")
    return p


def _ensure_split_mask(mask_path, w, full_h, feather, side="top"):
    """Generate soft alpha feather mask PNG for split-screen B-roll seam blending."""
    from PIL import Image

    p = Path(mask_path)
    if p.exists() and p.stat().st_size > 200:
        return p
    feather = max(8, min(full_h // 2, int(feather)))
    # Build 1-pixel-wide vertical gradient and resize across width (instant in Pillow)
    col = Image.new("L", (1, full_h), 255)
    cpx = col.load()
    for y in range(feather):
        t = y / float(feather)
        s = int(255 * (t * t * (3.0 - 2.0 * t)))
        if side == "top":
            cpx[0, full_h - 1 - y] = s
        else:
            cpx[0, y] = s
    alpha = col.resize((w, full_h), Image.Resampling.NEAREST)
    # FFmpeg alphamerge reads LUMINANCE (Y) of the mask stream — set RGB luminance = alpha!
    alpha.convert("RGB").save(str(p), "PNG")
    return p


def _ensure_rounded_mask(mask_path, w, h, radius=28):
    """Generate crisp anti-aliased rounded-rectangle mask PNG (luminance=alpha for FFmpeg alphamerge)."""
    from PIL import Image, ImageDraw

    p = Path(mask_path)
    if p.exists() and p.stat().st_size > 200:
        return p
    mask = Image.new("L", (w * 2, h * 2), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * 2 - 1, h * 2 - 1], radius=radius * 2, fill=255)
    mask = mask.resize((w, h), Image.Resampling.LANCZOS)
    mask.convert("RGB").save(str(p), "PNG")
    return p


def _prepare_card_png(src_img_path, out_png_path, remove_bg=True, max_dim=560):
    """Prepare uploaded card/product image as crisp RGBA PNG with studio flood-fill BG removal & clean drop shadow."""
    from collections import deque
    from PIL import Image, ImageDraw, ImageFilter

    im = Image.open(str(src_img_path)).convert("RGBA")
    im.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    w, h = im.size

    # Check if image already has meaningful transparency
    alpha_ext = im.getchannel("A").getextrema()
    has_alpha = alpha_ext[0] < 240

    if remove_bg and not has_alpha and w >= 16 and h >= 16:
        px = im.load()
        # Sample all 4 corners and edge midpoints to estimate studio background color robustly
        border_pts = []
        for fx in (2, w // 4, w // 2, (3 * w) // 4, w - 3):
            border_pts.append(px[fx, 2][:3])
            border_pts.append(px[fx, h - 3][:3])
        for fy in (h // 4, h // 2, (3 * h) // 4):
            border_pts.append(px[2, fy][:3])
            border_pts.append(px[w - 3, fy][:3])
        med = tuple(sorted(s[c] for s in border_pts)[len(border_pts) // 2] for c in range(3))
        close_cnt = sum(
            1 for s in border_pts
            if ((s[0] - med[0]) ** 2 + (s[1] - med[1]) ** 2 + (s[2] - med[2]) ** 2) <= 72 * 72
        )
        if close_cnt >= len(border_pts) * 0.65:
            max_bg_dist2 = 76 * 76
            max_step_dist2 = 28 * 28
            visited = bytearray(w * h)
            bg_mask = bytearray(w * h)
            q = deque()
            for x in range(w):
                for y in (0, h - 1):
                    r, g, b, _ = px[x, y]
                    if ((r - med[0]) ** 2 + (g - med[1]) ** 2 + (b - med[2]) ** 2) <= max_bg_dist2:
                        q.append((x, y))
            for y in range(h):
                for x in (0, w - 1):
                    r, g, b, _ = px[x, y]
                    if ((r - med[0]) ** 2 + (g - med[1]) ** 2 + (b - med[2]) ** 2) <= max_bg_dist2:
                        q.append((x, y))

            while q:
                cx, cy = q.popleft()
                idx = cy * w + cx
                if visited[idx]:
                    continue
                visited[idx] = 1
                bg_mask[idx] = 1
                cr, cg, cb, _ = px[cx, cy]
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        nidx = ny * w + nx
                        if visited[nidx]:
                            continue
                        nr, ng, nb, _ = px[nx, ny]
                        d_med = (nr - med[0]) ** 2 + (ng - med[1]) ** 2 + (nb - med[2]) ** 2
                        d_step = (nr - cr) ** 2 + (ng - cg) ** 2 + (nb - cb) ** 2
                        if d_med <= max_bg_dist2 and d_step <= max_step_dist2:
                            q.append((nx, ny))

            removed_ratio = sum(bg_mask) / float(w * h)
            if 0.06 < removed_ratio < 0.94:
                a_img = Image.new("L", (w, h), 255)
                apx = a_img.load()
                for y in range(h):
                    row_off = y * w
                    for x in range(w):
                        if bg_mask[row_off + x]:
                            apx[x, y] = 0
                # Erode 1px fringe halo along foreground boundary, then gently feather
                a_img = a_img.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))
                im.putalpha(a_img)
                has_alpha = True

    if not has_alpha:
        # Card / screenshot mode: apply crisp rounded corners
        rad = max(16, min(w, h) // 10)
        rmask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(rmask).rounded_rectangle([0, 0, w - 1, h - 1], radius=rad, fill=255)
        im.putalpha(rmask)

    # Trim empty transparent margins and add clean soft shadow
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    cw, ch = im.size
    pad = 18
    canvas = Image.new("RGBA", (cw + pad * 2, ch + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 150))
    sh.putalpha(im.getchannel("A").point(lambda v: int(v * 0.42)))
    canvas.paste(sh, (pad, pad + 6))
    canvas = canvas.filter(ImageFilter.GaussianBlur(5))
    canvas.paste(im, (pad, pad), im)
    canvas.save(str(out_png_path), "PNG")
    return out_png_path


def pick_impact_moments(captions, min_gap_s=5.0, max_ratio=0.35):
    """Select key narrative cuts/phrases where an automatic close-up zoom punch-in fits best."""
    if not captions:
        return []
    scored = []
    for idx, c in enumerate(captions):
        txt = c["text"]
        sc = 0.0
        if c["s"] <= 3.5:
            sc += 3.0
        if "?" in txt or "!" in txt:
            sc += 2.4
        if idx > 0 and (float(c["s"]) - float(captions[idx - 1]["e"])) >= 0.35:
            sc += 1.6  # Clean natural cut boundary
        if re.search(r"\d+|%|reais|mil\b|milh", txt, re.I):
            sc += 2.6
        for wd in re.findall(r"[a-zà-ú]+", txt.lower()):
            if wd in _IMPACT_WORDS:
                sc += 2.0
            elif len(wd) >= 8:
                sc += 0.5
        if sc > 0:
            s = max(0.0, float(c["s"]))
            raw_e = float(c["e"])
            # Extend zoom hold cleanly through the phrase cut (1.8s–3.8s, clamped before next gap)
            next_s = float(captions[idx + 1]["s"]) if idx + 1 < len(captions) else (raw_e + 1.5)
            e = min(next_s, max(s + 1.8, min(s + 3.8, raw_e + 0.35)))
            scored.append((sc, round(s, 3), round(e, 3)))
    scored.sort(key=lambda x: (-x[0], x[1]))
    chosen = []
    limit = max(1, int(len(captions) * max_ratio))
    for sc, s, e in scored:
        if len(chosen) >= limit:
            break
        if all(abs(s - cs) >= min_gap_s and (e <= cs or s >= ce + 0.5) for cs, ce in chosen):
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




def generate_ass(
    captions,
    out_path,
    width=1080,
    height=1920,
    style_id="highlight-words",
    accent_hex="",
    text_color="#FFFFFF",
    pos_y_pct=74,
    alignment="center",
    caption_lines=3,
    caption_scale=100,
    letter_spacing=0,
    line_spacing=1.0,
    outline_val=0.8,
    shadow_val=2.0,
    anim_in="",
    anim_out="fade-out",
    anim_dur=0.28,
    anim_intensity=1.0,
    main_font_id="",
    small_font_id="",
    caption_bold=False,
    highlight_fx="auto",
    gfx_cfg=None,
    fullscreen_mode="auto",
):
    """
    Generate CapCut/editorial-grade ASS subtitles backed by library_catalog.py & compositor.py.
    Supports the 6 core caption models + real bold font mapping + all 11 entry/exit animations
    + full typography overrides + editable vector graphic effects + manual breaks & multi-highlight.
    """
    cfg = resolve_caption_model(style_id)
    font_overrides = {
        "bebas": ("Bebas Neue", "BebasNeue-Regular.ttf", -1, 0),
        "coolvetica": ("Coolvetica", "Coolvetica-Regular.otf", -1, 0),
        "lucette": ("Lucette", "Lucette-Regular.ttf", -1, 0),
        "creato-bold-italic": ("Creato Display", "CreatoDisplay-BoldItalic.otf", -1, -1),
        "creato-extrabold-italic": ("Creato Display", "CreatoDisplay-ExtraBoldItalic.otf", -1, -1),
        "creato-extrabold": ("Creato Display", "CreatoDisplay-ExtraBold.otf", -1, 0),
        "apple-garamond": ("Apple Garamond", "AppleGaramond-BoldItalic.ttf", -1, -1),
        "apple-garamond-bold": ("Apple Garamond", "AppleGaramond-BoldItalic.ttf", -1, -1),
        "apple-garamond-light": ("Apple Garamond", "AppleGaramond-BoldItalic.ttf", -1, -1),
        "lavish": ("Lavish", "lavish.otf", -1, 0),
        "geist": ("Geist", "Geist.ttf", -1, 0),
        "dm-sans": ("DM Sans 9pt", "DMSans.ttf", -1, 0),
    }
    _BOLD_REAL_MAP = {
        "CreatoDisplay-Light.otf": ("Creato Display", "CreatoDisplay-ExtraBold.otf", -1, 0),
        "CreatoDisplay-Regular.otf": ("Creato Display", "CreatoDisplay-ExtraBold.otf", -1, 0),
        "CreatoDisplay-Medium.otf": ("Creato Display", "CreatoDisplay-Bold.otf", -1, 0),
        "AppleGaramond-LightItalic.ttf": ("Apple Garamond", "AppleGaramond-BoldItalic.ttf", -1, -1),
        "AppleGaramond-Italic.ttf": ("Apple Garamond", "AppleGaramond-BoldItalic.ttf", -1, -1),
    }
    if main_font_id and main_font_id in font_overrides:
        mf, mfile, mb, mi = font_overrides[main_font_id]
        cfg["main_font"], cfg["main_file"], cfg["main_bold"], cfg["main_italic"] = mf, mfile, -1, mi
    if cfg["main_file"] in _BOLD_REAL_MAP:
        bmf, bmfile, bmb, bmi = _BOLD_REAL_MAP[cfg["main_file"]]
        cfg["main_font"], cfg["main_file"], cfg["main_bold"] = bmf, bmfile, bmb
        if cfg["main_italic"]:
            cfg["main_italic"] = bmi
    cfg["main_bold"] = -1

    small_font_overrides = {
        **font_overrides,
        "creato-regular": ("Creato Display", "CreatoDisplay-Regular.otf", 0, 0),
        "creato-light": ("Creato Display Light", "CreatoDisplay-Light.otf", 0, 0),
        "creato-medium": ("Creato Display Medium", "CreatoDisplay-Medium.otf", 0, 0),
        "apple-garamond": ("Apple Garamond", "AppleGaramond-Italic.ttf", 0, -1),
        "apple-garamond-light": ("Apple Garamond Light", "AppleGaramond-LightItalic.ttf", 0, -1),
    }
    if small_font_id and small_font_id in small_font_overrides:
        sf, sfile, sb, si = small_font_overrides[small_font_id]
        cfg["small_font"], cfg["small_file"], cfg["small_bold"], cfg["small_italic"] = sf, sfile, sb, si
    if caption_bold:
        cfg["small_bold"] = -1
        if cfg["small_file"] in _BOLD_REAL_MAP:
            bsf, bsfile, _, _ = _BOLD_REAL_MAP[cfg["small_file"]]
            cfg["small_font"], cfg["small_file"] = bsf, bsfile
    cfg["main_bold"] = -1

    active_fx = cfg.get("default_fx", "none") if (not highlight_fx or highlight_fx == "auto") else highlight_fx
    if active_fx == "bar":
        active_fx = "pill"
    in_anim = (anim_in or cfg.get("default_anim_in") or "pop").strip().lower()
    out_anim = (anim_out or cfg.get("default_anim_out") or "fade-out").strip().lower()
    in_ms = max(120, min(850, int(float(anim_dur or 0.28) * 1000)))
    inten = max(0.35, min(1.6, float(anim_intensity or 1.0)))

    scale_f = min(width, height) / 1080.0
    user_scale = max(0.60, min(1.45, float(caption_scale or 100) / 100.0))
    s_size = max(20, int(cfg["small_size"] * scale_f * user_scale))
    m_size = max(28, int(cfg["main_size"] * scale_f * user_scale))
    outline = round(max(0.0, float(outline_val if outline_val is not None else 0.8) * scale_f), 1)
    shadow = round(max(0.0, float(shadow_val if shadow_val is not None else 2.0) * scale_f), 1)
    main_shadow = round(max(0.0, shadow * 0.55), 1)
    fsp_base = round(float(letter_spacing or 0) * scale_f, 1)
    line_mult = max(0.72, min(1.50, float(line_spacing or 1.0)))

    align_norm = (alignment or "center").strip().lower()
    an_code = 4 if align_norm == "left" else (6 if align_norm == "right" else 5)
    pos_x = int(width * (0.10 if align_norm == "left" else (0.90 if align_norm == "right" else 0.50)))
    pos_y = int(height * max(16, min(86, float(pos_y_pct))) / 100.0)

    text_ass = _hex_to_ass_bgr((text_color or "").strip() or cfg.get("default_color", "#FFFFFF"))
    chosen_hex = (accent_hex or "").strip() or cfg["default_accent"]
    accent_ass = _hex_to_ass_bgr(chosen_hex)
    glow_blur = round(max(8.0, 16.0 * scale_f), 1)
    glow_bord = round(max(3.0, 5.5 * scale_f), 1)
    has_color_accent = chosen_hex.upper() not in ("#FFFFFF", "FFFFFF")
    glow_alpha = "&H5E&" if has_color_accent else "&H7C&"

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Small,{cfg['small_font']},{s_size},{text_ass},{text_ass},&HE4000000,&H9E000000,{cfg['small_bold']},{cfg['small_italic']},0,0,100,100,{fsp_base},0,1,{outline},{shadow},{an_code},36,36,36,1
Style: Main,{cfg['main_font']},{m_size},{accent_ass},{accent_ass},&HF4000000,&HC8000000,{cfg['main_bold']},{cfg['main_italic']},0,0,100,100,{fsp_base},0,1,0,{main_shadow},{an_code},36,36,36,1
Style: MainGlow,{cfg['main_font']},{m_size},{accent_ass},{accent_ass},{accent_ass},&HFF000000,{cfg['main_bold']},{cfg['main_italic']},0,0,100,100,{fsp_base},0,1,{glow_bord},0,{an_code},36,36,36,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    req_lines = int(caption_lines or 3)
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
        extra_sp = max(0.0, fsp_base) * max(0, len(txt) - 1)
        if font_obj is not None:
            try:
                base_sz = m_size if is_main else s_size
                return float(font_obj.getlength(txt)) * (sz / max(base_sz, 1)) + extra_sp
            except Exception:
                pass
        return len(txt) * sz * 0.50 + extra_sp

    def _word_score(w):
        clean = re.sub(r"[^\w\u00e0-\u00fa\u00c0-\u00da]", "", w["w"])
        sc = len(clean)
        if clean.lower() in _IMPACT_WORDS:
            sc += 12
        return sc

    def _word_reveal(rel_ms, dur_ms, is_glow=False, is_main_tok=False):
        t0 = max(0, int(rel_ms)) if in_anim == "stagger" else 0
        fade_ms = 40 if in_anim == "none" else min(220, int(in_ms * 0.65))
        exit_dur = 40 if out_anim == "none" else min(180, max(70, int(dur_ms * 0.16)))
        exit_s = max(t0 + fade_ms + 30, dur_ms - exit_dur)
        exit_tag = f"\\t({exit_s},{dur_ms},2.1,\\alpha&HFF&)" if (out_anim != "none" and dur_ms > (t0 + fade_ms + 90)) else ""
        start_alpha = "\\alpha&H00&" if in_anim == "none" else "\\alpha&HFF&"
        if is_glow:
            if in_anim == "none":
                return f"\\1a{glow_alpha}\\3a&H82&\\4a&HFF&{exit_tag}"
            return f"{start_alpha}\\t({t0},{t0 + fade_ms},0.35,\\1a{glow_alpha}\\3a&H82&\\4a&HFF&){exit_tag}"
        if is_main_tok:
            if in_anim == "none":
                return f"\\1a&H00&\\3a&HF4&\\4a&HC8&{exit_tag}"
            return f"{start_alpha}\\t({t0},{t0 + fade_ms},0.35,\\1a&H00&\\3a&HF4&\\4a&HC8&){exit_tag}"
        if in_anim == "none":
            return f"\\1a&H00&\\3a&HE4&\\4a&H9E&{exit_tag}"
        return f"{start_alpha}\\t({t0},{t0 + fade_ms},0.35,\\1a&H00&\\3a&HE4&\\4a&H9E&){exit_tag}"

    def _entry_motion(x, y, dur_ms, is_main=False, target_scale=100, is_glow=False, est_w_px=300.0, row_h_px=90.0):
        d = int(28 * scale_f * inten)
        exit_dur = min(160, max(70, int(dur_ms * 0.16)))
        exit_s = max(in_ms + 40, dur_ms - exit_dur)
        s_exit = max(58, int(target_scale * (0.90 if out_anim == "scale-in" else 0.96)))
        exit_tag = ""
        if dur_ms > in_ms + 90 and out_anim != "none":
            if out_anim == "slide-up":
                exit_tag = f"\\move({x},{y},{x},{y - d},{exit_s},{dur_ms})"
            elif out_anim == "slide-down":
                exit_tag = f"\\move({x},{y},{x},{y + d},{exit_s},{dur_ms})"
            else:
                exit_tag = f"\\t({exit_s},{dur_ms},2.1,\\fscx{s_exit}\\fscy{s_exit})"

        if in_anim == "none":
            return f"\\pos({x},{y})\\fscx{target_scale}\\fscy{target_scale}"
        if in_anim == "scale-in":
            s_lo = max(45, int(target_scale * (0.74 if is_main else 0.86)))
            sp_tag = f"\\fsp{max(8, int(22 * scale_f))}\\t(0,{in_ms},0.3,\\fsp{fsp_base})" if (cfg["id"] == "big-word" and is_main) else ""
            return f"\\pos({x},{y})\\fscx{s_lo}\\fscy{s_lo}\\t(0,{in_ms},0.30,\\fscx{target_scale}\\fscy{target_scale}){sp_tag}{exit_tag}"
        if in_anim == "reveal":
            half_rw = int((est_w_px * (target_scale / 100.0)) / 2.0) + int(28 * scale_f)
            half_rh = int((row_h_px * (target_scale / 100.0)) * 0.78) + int(22 * scale_f)
            ax0 = x if align_norm == "left" else (x - half_rw * 2 if align_norm == "right" else x - half_rw)
            ax1 = ax0 + half_rw * 2
            cx0, cx1 = max(0, ax0), min(width, ax1)
            cy0, cy1 = max(0, y - half_rh), min(height, y + half_rh)
            return f"\\pos({x},{y})\\fscx{target_scale}\\fscy{target_scale}\\clip({cx0},{cy0},{cx0 + 6},{cy1})\\t(0,{in_ms},0.35,\\clip({cx0},{cy0},{cx1},{cy1})){exit_tag}"
        if in_anim == "slide-up":
            return f"\\move({x},{y + d},{x},{y},0,{in_ms})\\fscx{target_scale}\\fscy{target_scale}{exit_tag}"
        if in_anim == "slide-down":
            return f"\\move({x},{y - d},{x},{y},0,{in_ms})\\fscx{target_scale}\\fscy{target_scale}{exit_tag}"
        if in_anim == "slide-left":
            return f"\\move({x + int(d * 1.4)},{y},{x},{y},0,{in_ms})\\fscx{target_scale}\\fscy{target_scale}{exit_tag}"
        if in_anim == "slide-right":
            return f"\\move({x - int(d * 1.4)},{y},{x},{y},0,{in_ms})\\fscx{target_scale}\\fscy{target_scale}{exit_tag}"
        if in_anim == "pop":
            s_lo = max(48, int(target_scale * (0.78 if is_main else 0.90)))
            s_hi = int(target_scale * (1.06 if is_main else 1.02))
            t_mid = int(in_ms * 0.60)
            return f"\\pos({x},{y})\\fscx{s_lo}\\fscy{s_lo}\\t(0,{t_mid},0.34,\\fscx{s_hi}\\fscy{s_hi})\\t({t_mid},{in_ms},0.5,\\fscx{target_scale}\\fscy{target_scale}){exit_tag}"
        # fade-in / stagger / draw fallback
        s_lo = max(65, int(target_scale * 0.95))
        return f"\\pos({x},{y})\\fscx{s_lo}\\fscy{s_lo}\\t(0,{in_ms},0.30,\\fscx{target_scale}\\fscy{target_scale}){exit_tag}"

    def _inline_switch(is_main_tok, is_glow=False, main_sz_override=None):
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
            fg_c = "&H00FFFFFF&" if active_fx == "pill" else accent_ass
            return (
                f"\\fn{cfg['main_font']}\\fs{msz}\\b-1\\i{cfg['main_italic']}"
                f"\\1c{fg_c}\\3c&HF4000000&\\4c&HC8000000&\\bord0\\shad{main_shadow}\\blur0.7"
            )
        return (
            f"\\fn{cfg['small_font']}\\fs{s_size}\\b{cfg['small_bold']}\\i{cfg['small_italic']}"
            f"\\1c{text_ass}\\3c&HE4000000&\\4c&H9E000000&\\bord{outline}\\shad{shadow}\\blur0.7"
        )

    def _emit_mixed_line(tokens, x_center, y_row, cap_s, cap_e, t0s, t1s, main_local_set=None, inline_main_scale=1.0, row_fx="none"):
        if not tokens:
            return
        m_set = set(main_local_set or [])
        has_main = bool(m_set)
        primary_m = min(m_set) if has_main else None
        dur_ms = max(120, int((cap_e + 0.12 - cap_s) * 1000))
        max_w = width * 0.86
        inline_m_sz = max(s_size + 4, int(m_size * inline_main_scale)) if has_main else m_size
        est_w = 0.0
        for idx, w in enumerate(tokens):
            is_m = idx in m_set
            txt = w["w"].upper() if (is_m and cfg["upper"]) else w["w"]
            est_w += _measure(txt, is_main=is_m, custom_sz=(inline_m_sz if is_m else s_size))
        est_w += _measure(" ", is_main=False) * max(0, len(tokens) - 1)
        fit_pct = min(100, max(54, int((max_w / max(est_w, 1.0)) * 100)))
        half_w = (est_w * (fit_pct / 100.0)) / 2.0
        if align_norm == "center":
            safe_x = int(max(width * 0.07 + half_w, min(width * 0.93 - half_w, x_center)))
            if half_w * 2 > width * 0.82:
                safe_x = pos_x
        else:
            safe_x = x_center

        if has_main and row_fx not in ("none", ""):
            solo_m = (len(tokens) == 1)
            mtok = tokens[primary_m]
            mtxt = mtok["w"].upper() if cfg["upper"] else mtok["w"]
            mw_px = _measure(mtxt, is_main=True, custom_sz=inline_m_sz) * (fit_pct / 100.0)
            cx_m = safe_x
            if align_norm == "left":
                left_w = sum(_measure(t["w"], is_main=(j in m_set), custom_sz=(inline_m_sz if j in m_set else s_size)) for j, t in enumerate(tokens[:primary_m])) + _measure(" ", is_main=False) * primary_m
                cx_m = int(safe_x + left_w * (fit_pct / 100.0) + mw_px * 0.5)
            elif align_norm == "right":
                right_w = sum(_measure(t["w"], is_main=(j in m_set), custom_sz=(inline_m_sz if j in m_set else s_size)) for j, t in enumerate(tokens[primary_m + 1:], primary_m + 1)) + _measure(" ", is_main=False) * max(0, len(tokens) - primary_m - 1)
                cx_m = int(safe_x - right_w * (fit_pct / 100.0) - mw_px * 0.5)
            elif not solo_m:
                left_w = sum(_measure(t["w"], is_main=(j in m_set), custom_sz=(inline_m_sz if j in m_set else s_size)) for j, t in enumerate(tokens[:primary_m])) + _measure(" ", is_main=False) * primary_m
                cx_m = int(safe_x - half_w + left_w * (fit_pct / 100.0) + mw_px * 0.5)
            m_start_s = max(cap_s, float(mtok.get("s", cap_s)))
            mt0s = _fmt_ass_time(m_start_s)
            m_dur_ms = max(240, int((cap_e + 0.12 - m_start_s) * 1000))
            emit_ass_graphic_fx(
                events, row_fx, cx_m, y_row, mw_px, inline_m_sz * (fit_pct / 100.0),
                mt0s, t1s, m_dur_ms, scale_f, accent_ass, gfx_cfg=gfx_cfg,
            )

        if has_main:
            solo_main_glow = (len(tokens) == 1)
            glow_motion = _entry_motion(safe_x, y_row, dur_ms, is_main=solo_main_glow, target_scale=fit_pct, is_glow=True, est_w_px=est_w, row_h_px=inline_m_sz)
            g_chunks = []
            for idx, w in enumerate(tokens):
                is_m = idx in m_set
                txt = w["w"].upper() if (is_m and cfg["upper"]) else w["w"]
                if is_m:
                    rel_ms = max(0, (float(w["s"]) - cap_s) * 1000)
                    sw = _inline_switch(True, is_glow=True, main_sz_override=inline_m_sz)
                    g_chunks.append(f"{{{sw}{_word_reveal(rel_ms, dur_ms, is_glow=True, is_main_tok=True)}}}{txt}")
                else:
                    sw = _inline_switch(False, is_glow=True, main_sz_override=inline_m_sz)
                    g_chunks.append(f"{{{sw}}}{txt}")
            glow_base_style = "MainGlow" if solo_main_glow else "Small"
            glow_text = f" {{{_inline_switch(False, is_glow=True)}}}".join(g_chunks) if not solo_main_glow else g_chunks[0]
            if row_fx != "pill":
                events.append(
                    f"Dialogue: 1,{t0s},{t1s},{glow_base_style},,0,0,0,,{{\\an{an_code}{glow_motion}\\blur{glow_blur}}}{glow_text}"
                )

        solo_main = (has_main and len(tokens) == 1)
        motion = _entry_motion(safe_x, y_row, dur_ms, is_main=solo_main, target_scale=fit_pct, is_glow=False, est_w_px=est_w, row_h_px=(inline_m_sz if has_main else s_size))
        fg_chunks = []
        for idx, w in enumerate(tokens):
            is_m = idx in m_set
            txt = w["w"].upper() if (is_m and cfg["upper"]) else w["w"]
            rel_ms = max(0, (float(w["s"]) - cap_s) * 1000)
            rev = _word_reveal(rel_ms, dur_ms, is_glow=False, is_main_tok=is_m)
            if (has_main and not solo_main) or (is_m and row_fx == "pill"):
                sw = _inline_switch(is_m, is_glow=False, main_sz_override=inline_m_sz)
                fg_chunks.append(f"{{{sw}{rev}}}{txt}")
            else:
                fg_chunks.append(f"{{{rev}}}{txt}")

        style_name = "Main" if solo_main else "Small"
        layer_id = 2 if has_main else 0
        fg_text = f" {{{_inline_switch(False, is_glow=False)}}}".join(fg_chunks) if (has_main and not solo_main) else " ".join(fg_chunks)
        events.append(
            f"Dialogue: {layer_id},{t0s},{t1s},{style_name},,0,0,0,,{{\\an{an_code}{motion}\\blur0.7}}{fg_text}"
        )

    def _split_two_balanced(tokens, m_idx):
        n = len(tokens)
        best_k = max(1, min(n - 1, (m_idx + 1) if m_idx < n - 1 else n - 1))
        best_cost = 1e9
        for k in range(1, n):
            r1, r2 = tokens[:k], tokens[k:]
            cost = abs(sum(len(t["w"]) for t in r1) - sum(len(t["w"]) for t in r2))
            if len(r1) == 1 and m_idx != 0:
                cost += 25
            if len(r2) == 1 and m_idx != k:
                cost += 25
            if k == m_idx or k == m_idx + 1:
                cost -= 2
            if cost < best_cost:
                best_cost, best_k = cost, k
        return tokens[:best_k], tokens[best_k:]

    for c in captions:
        raw_text = (c.get("text") or "").strip()
        words = c.get("words") or []
        if not raw_text and not words:
            continue
        cap_s, cap_e = float(c["s"]), float(c["e"])
        if not words:
            toks = raw_text.replace("|", " ").replace("\n", " ").split()
            step = max(0.08, (cap_e - cap_s) / max(1, len(toks)))
            words = [{"w": tok, "s": cap_s + i * step, "e": cap_s + (i + 1) * step} for i, tok in enumerate(toks)]

        t0s, t1s = _fmt_ass_time(cap_s), _fmt_ass_time(cap_e + 0.12)
        if c.get("main_indices"):
            m_indices = [int(i) for i in c["main_indices"] if 0 <= int(i) < len(words)]
        elif c.get("main_idx") is not None and 0 <= int(c["main_idx"]) < len(words):
            m_indices = [int(c["main_idx"])]
        else:
            m_indices = [max(range(len(words)), key=lambda i: _word_score(words[i]))]
        m_set_all = set(m_indices)
        main_idx = m_indices[0] if m_indices else 0
        cap_fx = c.get("graphic_fx") or active_fx
        if cap_fx == "bar":
            cap_fx = "pill"

        # Editorial Serif fullscreen scene backdrop when explicitly enabled or full-sentence punctuation matches
        is_full_bg = (fullscreen_mode == "on") or bool(c.get("fullscreen")) or (
            cfg.get("fullscreen_backdrop") and fullscreen_mode != "off" and len(words) <= 3 and ("." in raw_text or "!" in raw_text)
        )
        if is_full_bg:
            events.append(
                f"Dialogue: 0,{t0s},{t1s},Main,,0,0,0,,"
                f"{{\\an7\\pos(0,0)\\p1\\1c&H000000&\\1a&H42&\\bord0\\shad0}}m 0 0 l {width} 0 l {width} {height} l 0 {height}{{\\p0}}"
            )

        # Layered Typography background depth echo behind foreground text
        if cfg.get("layered_overlap") and words:
            bg_word = words[main_idx]["w"].upper()
            bg_sz = int(m_size * 1.65)
            bg_y = max(int(height * 0.16), pos_y - int(m_size * 0.12))
            events.append(
                f"Dialogue: 0,{t0s},{t1s},Main,,0,0,0,,"
                f"{{\\an5\\pos({pos_x},{bg_y})\\fn{cfg['main_font']}\\fs{bg_sz}\\b-1\\1c&HFFFFFF&\\1a&HC4&\\bord0\\shad0\\blur2.4}}{bg_word}"
            )

        # Manual line breaks using '|' or newline
        if "|" in raw_text or "\n" in raw_text:
            parts = [p.strip().split() for p in re.split(r"[|\n]+", raw_text) if p.strip()]
            cursor = 0
            n_rows = len(parts)
            step_y = int((m_size * 0.56 + s_size * 0.44) * line_mult)
            y_start = pos_y - int(((n_rows - 1) * step_y) / 2)
            for r_idx, ptoks in enumerate(parts):
                cnt = len(ptoks)
                row_tokens = words[cursor:cursor + cnt] if cursor + cnt <= len(words) else [{"w": t, "s": cap_s, "e": cap_e} for t in ptoks]
                row_m = {j for j in range(len(row_tokens)) if (cursor + j) in m_set_all}
                _emit_mixed_line(row_tokens, pos_x, y_start + r_idx * step_y, cap_s, cap_e, t0s, t1s, main_local_set=row_m, inline_main_scale=0.92 if len(row_tokens) > 1 else 1.0, row_fx=cap_fx)
                cursor += cnt
            continue

        if req_lines == 1 or len(words) == 1:
            _emit_mixed_line(words, pos_x, pos_y, cap_s, cap_e, t0s, t1s, main_local_set=m_set_all, inline_main_scale=0.88, row_fx=cap_fx)
            continue

        before = words[:main_idx]
        main_w = [words[main_idx]]
        after = words[main_idx + 1:]
        upper_main = cfg["upper"]
        fx_pad = int(m_size * (0.20 if cap_fx in ("circle", "pill", "arrow") else 0.12 if cap_fx == "underline" else 0.0))
        mb_has = any(i < len(before) for i in m_set_all)
        ma_has = any(i > main_idx for i in m_set_all)
        top_offset = int(((m_size * 0.44 + (m_size * 0.34 if mb_has else s_size * 0.32))) * line_mult) + fx_pad
        bot_offset = int(((m_size * (0.42 if upper_main else 0.46) + (m_size * 0.36 if ma_has else s_size * 0.35))) * line_mult) + fx_pad
        top_2_above = int((m_size * 0.28 + s_size * 0.32) * line_mult) + fx_pad
        bot_2_below = int(m_size * 0.16 * line_mult) + fx_pad
        top_2_main = int(m_size * 0.16 * line_mult) + fx_pad
        bot_2_after = int((m_size * (0.24 if upper_main else 0.28) + s_size * 0.36) * line_mult) + fx_pad

        if req_lines >= 3 and before and after:
            orphan_before = (len(before) == 1 and len(before[0]["w"]) <= 4 and len(after) >= 2)
            orphan_after = (len(after) == 1 and len(after[0]["w"]) <= 4 and len(before) >= 2)
            if orphan_before or orphan_after:
                r1, r2 = _split_two_balanced(words, main_idx)
                m1 = {i for i in m_set_all if i < len(r1)}
                m2 = {i - len(r1) for i in m_set_all if i >= len(r1)}
                _emit_mixed_line(r1, pos_x, pos_y - top_2_above, cap_s, cap_e, t0s, t1s, main_local_set=m1, inline_main_scale=0.92 if m1 else 1.0, row_fx=cap_fx)
                _emit_mixed_line(r2, pos_x, pos_y + bot_2_after, cap_s, cap_e, t0s, t1s, main_local_set=m2, inline_main_scale=0.92 if m2 else 1.0, row_fx=cap_fx)
            else:
                mb = {i for i in m_set_all if i < len(before)}
                ma = {i - (main_idx + 1) for i in m_set_all if i > main_idx}
                _emit_mixed_line(before, pos_x, pos_y - top_offset, cap_s, cap_e, t0s, t1s, main_local_set=mb, row_fx=cap_fx)
                _emit_mixed_line(main_w, pos_x, pos_y, cap_s, cap_e, t0s, t1s, main_local_set={0}, inline_main_scale=1.0, row_fx=cap_fx)
                _emit_mixed_line(after, pos_x, pos_y + bot_offset, cap_s, cap_e, t0s, t1s, main_local_set=ma, row_fx=cap_fx)
        elif req_lines == 2:
            r1, r2 = _split_two_balanced(words, main_idx)
            m1 = {i for i in m_set_all if i < len(r1)}
            m2 = {i - len(r1) for i in m_set_all if i >= len(r1)}
            y1 = pos_y - (top_2_main if (0 in m1 and len(r1) == 1) else top_2_above)
            y2 = pos_y + (bot_2_below if (0 in m2 and len(r2) == 1) else bot_2_after)
            _emit_mixed_line(r1, pos_x, y1, cap_s, cap_e, t0s, t1s, main_local_set=m1, inline_main_scale=0.94 if m1 else 1.0, row_fx=cap_fx)
            _emit_mixed_line(r2, pos_x, y2, cap_s, cap_e, t0s, t1s, main_local_set=m2, inline_main_scale=0.94 if m2 else 1.0, row_fx=cap_fx)
        elif before:
            mb = {i for i in m_set_all if i < len(before)}
            _emit_mixed_line(before, pos_x, pos_y - top_2_above, cap_s, cap_e, t0s, t1s, main_local_set=mb, row_fx=cap_fx)
            _emit_mixed_line(main_w, pos_x, pos_y + bot_2_below, cap_s, cap_e, t0s, t1s, main_local_set={0}, inline_main_scale=1.0, row_fx=cap_fx)
        else:
            ma = {i - (main_idx + 1) for i in m_set_all if i > main_idx}
            _emit_mixed_line(main_w, pos_x, pos_y - top_2_main, cap_s, cap_e, t0s, t1s, main_local_set={0}, inline_main_scale=1.0, row_fx=cap_fx)
            _emit_mixed_line(after, pos_x, pos_y + bot_2_after, cap_s, cap_e, t0s, t1s, main_local_set=ma, row_fx=cap_fx)

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


def render_video(
    src_path,
    out_path,
    keep_ranges,
    ass_path,
    impact_times,
    hw,
    zoom_enabled=True,
    width=1080,
    height=1920,
    studio_audio=False,
    broll_path=None,
    broll_layout="top",
    broll_start=None,
    broll_dur=3.5,
    broll_items=None,
    color_grade=False,
    card_path=None,
    card_anim="side-right",
    card_start=None,
    card_dur=3.2,
    card_items=None,
    compositions=None,
):
    ffmpeg, _ = find_ffmpeg()
    ass_escaped = str(ass_path).replace("\\", "/").replace(":", "\\:")
    fonts_escaped = str(FONTS_DIR).replace("\\", "/").replace(":", "\\:")

    src_info = probe_video(src_path)
    has_src_audio = bool(src_info.get("has_audio", True))

    w_even = width - (width % 2)
    h_even = height - (height % 2)

    # Normalize B-roll and Card queues (supporting single legacy args or multi-item lists)
    brolls = list(broll_items or [])
    if not brolls and broll_path and Path(broll_path).exists() and broll_start is not None:
        brolls.append({"path": broll_path, "layout": broll_layout, "start": broll_start, "dur": broll_dur})
    brolls = [b for b in brolls if b.get("path") and Path(b["path"]).exists() and b.get("start") is not None][:5]

    cards = list(card_items or [])
    if not cards and card_path and Path(card_path).exists() and card_start is not None:
        cards.append({"path": card_path, "anim": card_anim, "start": card_start, "dur": card_dur})
    cards = [c for c in cards if c.get("path") and Path(c["path"]).exists() and c.get("start") is not None][:6]

    # Build trim + concat filter if decupagem cut segments
    n_segs = len(keep_ranges)
    low_ram = hw.get("ram_gb", 8.0) <= 1.2

    # Cap export resolution to 720p on <=1.2GB containers to prevent OOM
    if low_ram and max(w_even, h_even) > 1280:
        if h_even >= w_even:
            w_even, h_even = 720, 1280
        else:
            w_even, h_even = 1280, 720
    scale_flags = "bilinear" if low_ram else "lanczos"
    scale_base = f"scale={w_even}:{h_even}:force_original_aspect_ratio=decrease:flags={scale_flags},pad={w_even}:{h_even}:(ow-iw)/2:(oh-ih)/2:black"

    total_keep_dur = max(0.5, sum(max(0.1, float(seg["e"]) - float(seg["s"])) for seg in keep_ranges))
    fc_parts = []
    concat_v = []
    concat_a = []
    if n_segs == 1 and keep_ranges[0]["s"] == 0.0 and float(keep_ranges[0]["e"]) >= float(src_info.get("duration") or 0.0) - 0.15:
        v_chain = "[0:v]"
        a_chain = "[0:a]" if has_src_audio else None
    elif n_segs > 6 or (low_ram and n_segs > 2):
        # Single-decoder CFR selection avoids N simultaneous trim decoders blowing container RAM!
        sel_expr = "+".join(f"between(t,{float(seg['s']):.3f},{float(seg['e']):.3f})" for seg in keep_ranges)
        fc_parts.append(f"[0:v]fps=30,{scale_base},select='{sel_expr}',setpts=N/(30*TB)[vsel]")
        v_chain = "[vsel]"
        if has_src_audio:
            fc_parts.append(f"[0:a]aresample=44100,aselect='{sel_expr}',asetpts=N/(44100*TB)[asel]")
            a_chain = "[asel]"
        else:
            a_chain = None
    else:
        for i, seg in enumerate(keep_ranges):
            s, e = seg["s"], seg["e"]
            fc_parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]")
            concat_v.append(f"[v{i}]")
            if has_src_audio:
                fc_parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]")
                concat_a.append(f"[a{i}]")
        if has_src_audio:
            pairs = "".join(f"{concat_v[i]}{concat_a[i]}" for i in range(n_segs))
            fc_parts.append(pairs + f"concat=n={n_segs}:v=1:a=1[vcat][acat]")
            a_chain = "[acat]"
        else:
            fc_parts.append("".join(concat_v) + f"concat=n={n_segs}:v=1:a=0[vcat]")
            a_chain = None
        v_chain = "[vcat]"

    pre_scaled_done = (v_chain == "[vsel]")

    # Instant jump-cut punch-in close-up focused near the speaker's upper/face framing (no bouncy keyframe drift!)
    zoom_filter = ""
    if zoom_enabled and impact_times:
        terms = []
        for imp_s, imp_e in impact_times[:10]:
            s_t = max(0.0, float(imp_s))
            e_t = max(s_t + 1.2, float(imp_e))
            terms.append(f"between(t,{s_t:.2f},{e_t:.2f})*0.24")
        if terms:
            z_expr = "1+" + "+".join(terms)
            zoom_filter = (
                f",scale=w='trunc(iw*({z_expr})/2)*2':h='trunc(ih*({z_expr})/2)*2':flags={scale_flags}:eval=frame,"
                f"crop=w={w_even}:h={h_even}:x='(iw-ow)/2':y='max(0,(ih-oh)*0.22)'"
            )

    extra_inputs = []
    next_in_idx = 1
    has_bokeh = bool(color_grade and not low_ram)

    broll_inputs = []
    img_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
    for b in brolls:
        bp = Path(b["path"])
        is_img = bp.suffix.lower() in img_exts
        broll_inputs.append((next_in_idx, b, is_img))
        next_in_idx += 1
        if is_img:
            extra_inputs += ["-loop", "1", "-i", str(bp)]
        else:
            extra_inputs += ["-i", str(bp)]

    card_inputs = []
    for c in cards:
        card_inputs.append((next_in_idx, c))
        next_in_idx += 1
        extra_inputs += ["-loop", "1", "-i", str(c["path"])]

    mask_idx = None
    if has_bokeh:
        mask_png = _ensure_bokeh_mask(Path(out_path).parent / f"bokeh_{w_even}x{h_even}.png", w_even, h_even, strength=0.65)
        mask_idx = next_in_idx
        next_in_idx += 1
        extra_inputs += ["-loop", "1", "-i", str(mask_png)]

    temp_artifacts = []
    # Pre-build gradient seam feather masks if split-screen B-rolls are used
    hh = (h_even // 2) - ((h_even // 2) % 2)
    feather_px = max(24, int(hh * 0.14))
    feather_px -= feather_px % 2
    b_full_h = hh + feather_px
    top_fmask_idx = bot_fmask_idx = None
    if broll_inputs:
        tmask_png = ensure_split_mask(Path(out_path).parent / f"split_top_{w_even}x{b_full_h}.png", w_even, b_full_h, feather_px, "top")
        bmask_png = ensure_split_mask(Path(out_path).parent / f"split_bot_{w_even}x{b_full_h}.png", w_even, b_full_h, feather_px, "bottom")
        temp_artifacts.extend([tmask_png, bmask_png])
        top_fmask_idx = next_in_idx
        next_in_idx += 1
        extra_inputs += ["-loop", "1", "-i", str(tmask_png)]
        bot_fmask_idx = next_in_idx
        next_in_idx += 1
        extra_inputs += ["-loop", "1", "-i", str(bmask_png)]

    # Support rich Professional Composition Models (floating-media, editorial-card, stacked-cards, visual-storytelling, split-composition)
    comp_list = list(compositions or [])
    comp_stages = []
    for ci_m, comp in enumerate(comp_list[:6]):
        ctype = (comp.get("type") or "floating-media").strip().lower()
        cs = max(0.0, float(comp.get("start") or 0.0))
        ce = max(cs + 1.4, float(comp.get("end") or (cs + 3.5)))
        cd = min(12.0, ce - cs)
        ce = cs + cd
        anim_in = (comp.get("anim_in") or "scale-in").lower()
        anim_out = (comp.get("anim_out") or "fade-out").lower()
        anim_dur = float(comp.get("anim_dur") or 0.34)
        anim_int = float(comp.get("anim_intensity") or 1.0)
        bg_hex = comp.get("bg_color") or "#FFFFFF"
        acc_hex = comp.get("accent_color") or "#F472B6"
        txt_hex = comp.get("text_color") or "#111827"
        rad = int(comp.get("radius") or 24)
        sh_pct = int(comp.get("shadow") or 55)
        media_list = list(comp.get("media") or [])

        if ctype == "editorial-card":
            m_src = media_list[0].get("path") if (media_list and media_list[0].get("path")) else None
            c_png = Path(out_path).parent / f"edcard_{ci_m}_{uuid.uuid4().hex[:6]}.png"
            card_w = max(240, int(w_even * (float(comp.get("scale") or 74) / 100.0)))
            card_w -= card_w % 2
            build_editorial_card_png(
                m_src, c_png, card_w=card_w,
                title=comp.get("title") or "", subtitle=comp.get("subtitle") or "",
                tag=comp.get("tag") or "", bg_hex=bg_hex, accent_hex=acc_hex, text_hex=txt_hex,
                radius=rad, shadow_pct=sh_pct,
            )
            temp_artifacts.append(c_png)
            c_idx = next_in_idx
            next_in_idx += 1
            extra_inputs += ["-loop", "1", "-i", str(c_png)]
            tx = f"(W-w)*{float(comp.get('x', 50))/100.0:.2f}"
            ty = f"{int(h_even * float(comp.get('y', 18))/100.0)}"
            comp_stages.append(("overlay_png", c_idx, cs, cd, anim_in, anim_out, anim_dur, anim_int, tx, ty))
        elif ctype in ("stacked-cards", "visual-storytelling"):
            angles = (-4.5, 3.5, 0.0) if ctype == "stacked-cards" else (-2.0, 2.0, 0.0)
            labels = list(comp.get("labels") or [])
            base_x = float(comp.get("x", 10 if ctype == "stacked-cards" else 8))
            base_y = float(comp.get("y", 14))
            for li, mitem in enumerate((media_list or [{"path": None}])[:3]):
                m_src = mitem.get("path")
                if m_src and not Path(m_src).exists():
                    continue
                is_story_main = (ctype == "visual-storytelling" and li == 0)
                c_w = max(200, int(w_even * (0.64 if is_story_main else (0.48 if ctype == "stacked-cards" else 0.36))))
                c_w -= c_w % 2
                c_png = Path(out_path).parent / f"stack_{ci_m}_{li}_{uuid.uuid4().hex[:6]}.png"
                sub_lbl = labels[li] if li < len(labels) else (comp.get("subtitle") or "" if li == 0 else "")
                build_editorial_card_png(
                    m_src, c_png, card_w=c_w,
                    title=(comp.get("title") or "") if li == 0 else sub_lbl,
                    subtitle=(comp.get("subtitle") or "") if li == 0 else "",
                    tag=(comp.get("tag") or "") if li == 0 else (sub_lbl if not is_story_main else ""),
                    bg_hex=bg_hex, accent_hex=acc_hex, text_hex=txt_hex,
                    radius=rad, shadow_pct=sh_pct, angle_deg=angles[li % len(angles)],
                )
                temp_artifacts.append(c_png)
                c_idx = next_in_idx
                next_in_idx += 1
                extra_inputs += ["-loop", "1", "-i", str(c_png)]
                st_delay = li * 0.24
                if ctype == "stacked-cards":
                    px_pct = min(65.0, base_x + li * 16.0)
                    py_pct = min(56.0, base_y + li * 12.0)
                else:
                    slots = [(8.0, 10.0), (54.0, 14.0), (52.0, 38.0)]
                    px_pct, py_pct = slots[li % len(slots)]
                tx = f"{int(w_even * px_pct / 100.0)}"
                ty = f"{int(h_even * py_pct / 100.0)}"
                in_k = "slide-left" if (li % 2 == 1 and anim_in == "stagger") else ("slide-right" if anim_in == "stagger" else anim_in)
                comp_stages.append(("overlay_png", c_idx, cs + st_delay, max(1.0, cd - st_delay), in_k, anim_out, anim_dur, anim_int, tx, ty))
        elif ctype == "floating-media":
            for fi, mitem in enumerate(media_list[:4]):
                mp = mitem.get("path")
                if not mp or not Path(mp).exists():
                    continue
                is_img = Path(mp).suffix.lower() in IMG_EXTS
                m_idx = next_in_idx
                next_in_idx += 1
                extra_inputs += (["-loop", "1", "-i", str(mp)] if is_img else ["-i", str(mp)])
                sc_p = float(comp.get("scale") or 40) / 100.0
                bw = max(160, int(w_even * sc_p))
                bh = max(140, int(h_even * sc_p * 0.56))
                bw -= bw % 2
                bh -= bh % 2
                st_delay = fi * 0.20 if anim_in == "stagger" else 0.0
                px_pct = min(82.0, float(comp.get("x", 6)) + fi * 14.0)
                py_pct = min(72.0, float(comp.get("y", 8)) + fi * 16.0)
                tx = f"{int(w_even * px_pct / 100.0)}"
                ty = f"{int(h_even * py_pct / 100.0)}"
                comp_stages.append(("floating", m_idx, is_img, bw, bh, rad, cs + st_delay, max(1.0, cd - st_delay), anim_in, anim_out, anim_dur, anim_int, tx, ty))
        elif ctype == "split-composition" and media_list:
            mp = media_list[0].get("path")
            if mp and Path(mp).exists():
                is_img = Path(mp).suffix.lower() in IMG_EXTS
                m_idx = next_in_idx
                next_in_idx += 1
                extra_inputs += (["-loop", "1", "-i", str(mp)] if is_img else ["-i", str(mp)])
                comp_stages.append(("split", m_idx, is_img, comp.get("orientation") or "vertical", float(comp.get("split_ratio") or 50), int(comp.get("gap") or 10), rad, acc_hex, comp.get("highlight_pane") or "a", cs, cd, anim_in, anim_out, anim_dur))

    use_fc = bool(fc_parts or broll_inputs or card_inputs or comp_stages or color_grade)
    af_chain = "highpass=f=65,acompressor=threshold=-22dB:ratio=1.7:attack=12:release=140:makeup=1.2,alimiter=limit=0.95" if (studio_audio and has_src_audio) else ""
    base_scale_step = "" if pre_scaled_done else scale_base

    if use_fc:
        grade_4k = ",unsharp=5:5:0.75:3:3:0.0,eq=contrast=1.08:saturation=1.14:brightness=0.02:gamma=1.02" if color_grade else ""
        prep_chain = f"{base_scale_step}{zoom_filter}{grade_4k}".lstrip(",")
        if prep_chain:
            fc_parts.append(f"{v_chain}{prep_chain}[vprep]")
            cur_v = "[vprep]"
        else:
            cur_v = v_chain

        if has_bokeh:
            fc_parts.append(
                f"{cur_v}split=2[vsharp][vbsrc];"
                f"[{mask_idx}:v]trim=duration={total_keep_dur:.3f},setpts=PTS-STARTPTS[bmask];"
                f"[vbsrc]scale=w=trunc(iw/3/2)*2:h=trunc(ih/3/2)*2,gblur=sigma=5,scale=w={w_even}:h={h_even}:flags=bilinear[vbokeh];"
                f"[vbokeh][bmask]alphamerge=shortest=1[vbokeh_a];"
                f"[vsharp][vbokeh_a]overlay=0:0:shortest=1[vgraded]"
            )
            cur_v = "[vgraded]"

        auto_b_cycle = ["top", "pip-rounded", "bottom", "center-frame", "full"]
        split_brolls = []
        framed_brolls = []
        strip_i = 0
        for bi, (b_idx, b, is_img) in enumerate(broll_inputs):
            b_dur_req = float(b.get("dur") or 3.5)
            if not is_img:
                b_info = probe_video(b["path"])
                b_dur = max(1.0, min(12.0, b_dur_req, float(b_info.get("duration") or b_dur_req)))
            else:
                b_dur = max(1.0, min(12.0, b_dur_req))
            bs = max(0.0, float(b["start"]))
            be = bs + b_dur
            layout = (b.get("layout") or "auto").lower()
            if layout == "auto":
                layout = auto_b_cycle[bi % len(auto_b_cycle)]
            if layout == "full":
                fc_parts.append(
                    f"[{b_idx}:v]trim=start=0:end={b_dur:.3f},setpts=PTS-STARTPTS,"
                    f"scale={w_even}:{h_even}:force_original_aspect_ratio=increase:flags={scale_flags},crop={w_even}:{h_even},format=rgba,"
                    f"fade=t=in:st=0:d=0.25:alpha=1,fade=t=out:st={max(0.1, b_dur-0.25):.3f}:d=0.25:alpha=1,setpts=PTS-STARTPTS+{bs:.3f}/TB,setsar=1[vb{bi}]"
                )
                fc_parts.append(f"{cur_v}[vb{bi}]overlay=0:0:enable='between(t,{bs:.3f},{be:.3f})':eof_action=pass[vbf{bi}]")
                cur_v = f"[vbf{bi}]"
            elif layout in ("pip-rounded", "center-frame", "triptych-strips"):
                framed_brolls.append((bi, b_idx, layout, bs, be, b_dur, strip_i))
                if layout == "triptych-strips":
                    strip_i += 1
            else:
                split_brolls.append((bi, b_idx, layout, bs, be, b_dur))

        for bi, b_idx, lay, bs, be, b_dur, s_ord in framed_brolls:
            if lay == "pip-rounded":
                bw, bh, rad = max(160, int(w_even * 0.38)), max(160, int(h_even * 0.22)), 26
                ox, oy = f"{int(w_even * 0.05)}", f"{int(h_even * 0.07)}"
            elif lay == "center-frame":
                bw, bh, rad = max(240, int(w_even * 0.78)), max(220, int(h_even * 0.42)), 34
                ox, oy = "(W-w)/2", f"{int(h_even * 0.22)}"
            else:  # triptych-strips: Video 1 sliding horizontal strip!
                bw, bh, rad = max(260, int(w_even * 0.78)), max(96, int(h_even * 0.14)), 20
                target_x = int((w_even - bw) * 0.5)
                tin = f"min(1,max(0,(t-{bs:.3f})/0.32))"
                e_in = f"(1-(1-{tin})*(1-{tin})*(1-{tin}))"
                ox = f"{w_even}-({w_even}-{target_x})*{e_in}"
                oy = f"{int(h_even * (0.09 + (s_ord % 3) * 0.17))}"
            bw -= bw % 2
            bh -= bh % 2
            rmask = ensure_rounded_mask(Path(out_path).parent / f"rmask_{bw}x{bh}_r{rad}.png", bw, bh, radius=rad)
            temp_artifacts.append(rmask)
            rmask_idx = next_in_idx
            next_in_idx += 1
            extra_inputs += ["-loop", "1", "-i", str(rmask)]
            fc_parts.append(f"[{rmask_idx}:v]trim=duration={b_dur:.3f},setpts=PTS-STARTPTS[rm{bi}]")
            fc_parts.append(
                f"[{b_idx}:v]trim=start=0:end={b_dur:.3f},setpts=PTS-STARTPTS,"
                f"scale={bw}:{bh}:force_original_aspect_ratio=increase:flags={scale_flags},crop={bw}:{bh},format=rgba[vbr_{bi}]"
            )
            fc_parts.append(
                f"[vbr_{bi}][rm{bi}]alphamerge=shortest=1,"
                f"fade=t=in:st=0:d=0.22:alpha=1,fade=t=out:st={max(0.1, b_dur-0.22):.3f}:d=0.22:alpha=1,"
                f"setpts=PTS-STARTPTS+{bs:.3f}/TB,setsar=1[vbfrm{bi}]"
            )
            fc_parts.append(f"{cur_v}[vbfrm{bi}]overlay=x='{ox}':y='{oy}':enable='between(t,{bs:.3f},{be:.3f})':eof_action=pass[vbf_{bi}]")
            cur_v = f"[vbf_{bi}]"

        if split_brolls:
            # Frame speaker cleanly into the visible half (biased toward top-center face so head is NEVER cropped!)
            face_crop_y = max(0, int(h_even * 0.10))
            for bi, b_idx, lay, bs, be, b_dur in split_brolls:
                # 1) Reframe speaker into opposite half during [bs, be]
                sp_y = int(hh) if lay == "top" else 0
                sp_h = h_even - int(hh)
                sp_h -= sp_h % 2
                fc_parts.append(f"{cur_v}split=2[vm{bi}_a][vm{bi}_b]")
                fc_parts.append(
                    f"[vm{bi}_b]crop=w={w_even}:h={sp_h}:x=0:y={min(face_crop_y, max(0, h_even - sp_h))},"
                    f"format=rgba,fade=t=in:st={bs:.3f}:d=0.25:alpha=1,fade=t=out:st={max(bs+0.1, be-0.25):.3f}:d=0.25:alpha=1[vsph{bi}]"
                )
                fc_parts.append(f"[vm{bi}_a][vsph{bi}]overlay=0:{sp_y}:enable='between(t,{bs:.3f},{be:.3f})'[vspbg{bi}]")

                # 2) Prepare B-roll with gradient feather mask on dividing seam + smooth entry/exit fade
                fmask_i = top_fmask_idx if lay == "top" else bot_fmask_idx
                b_overlay_y = 0 if lay == "top" else (h_even - b_full_h)
                fc_parts.append(f"[{fmask_i}:v]trim=duration={b_dur:.3f},setpts=PTS-STARTPTS[fm{bi}]")
                fc_parts.append(
                    f"[{b_idx}:v]trim=start=0:end={b_dur:.3f},setpts=PTS-STARTPTS,"
                    f"scale={w_even}:{b_full_h}:force_original_aspect_ratio=increase:flags={scale_flags},crop={w_even}:{b_full_h},format=rgba[vbraw{bi}]"
                )
                fc_parts.append(
                    f"[vbraw{bi}][fm{bi}]alphamerge=shortest=1,"
                    f"fade=t=in:st=0:d=0.28:alpha=1,fade=t=out:st={max(0.1, b_dur-0.28):.3f}:d=0.28:alpha=1,"
                    f"setpts=PTS-STARTPTS+{bs:.3f}/TB,setsar=1[vbfe{bi}]"
                )
                fc_parts.append(f"[vspbg{bi}][vbfe{bi}]overlay=0:{b_overlay_y}:enable='between(t,{bs:.3f},{be:.3f})':eof_action=pass[vbs{bi}]")
                cur_v = f"[vbs{bi}]"

        auto_c_cycle = ["side-right", "side-left", "corner-top"]
        cw_target = max(150, int(w_even * 0.32))
        cw_target -= cw_target % 2
        margin = max(22, int(w_even * 0.04))
        for ci, (c_idx, c) in enumerate(card_inputs):
            cs = max(0.0, float(c["start"]))
            cd = max(1.4, min(6.0, float(c.get("dur") or 3.2)))
            ce = cs + cd
            # Cubic smoothstep easing for both entry (0.34s) and exit (0.34s)
            tin = f"min(1,max(0,(t-{cs:.3f})/0.34))"
            tout = f"min(1,max(0,({ce:.3f}-t)/0.34))"
            ein = f"({tin}*{tin}*(3-2*{tin}))"
            eout = f"({tout}*{tout}*(3-2*{tout}))"
            cramp = f"({ein}*{eout})"
            bob = f"7*sin(3.0*(t-{cs:.3f})+{ci*1.1:.1f})"
            canim = (c.get("anim") or "auto").lower()
            if canim in ("auto", "behind-peek"):
                canim = auto_c_cycle[ci % len(auto_c_cycle)]
            slot_dy = (ci % 3) * int(h_even * 0.13)
            if canim == "side-left":
                cx = f"-w+(w+{margin})*{cramp}"
                cy = f"{int(h_even * 0.20) + slot_dy}+{bob}"
            elif canim == "corner-top":
                cx = f"{margin}" if ci % 2 == 1 else f"{w_even}-w-{margin}"
                cy = f"-h+(h+{int(h_even * 0.11)})*{cramp}+{bob}"
            else:
                cx = f"{w_even}-(w+{margin})*{cramp}"
                cy = f"{int(h_even * 0.20) + slot_dy}+{bob}"
            fc_parts.append(
                f"[{c_idx}:v]trim=duration={cd:.3f},scale={cw_target}:-2:flags={scale_flags},format=rgba,"
                f"fade=t=in:st=0:d=0.30:alpha=1,fade=t=out:st={max(0.1, cd-0.30):.3f}:d=0.30:alpha=1,"
                f"setpts=PTS-STARTPTS+{cs:.3f}/TB[vcard{ci}]"
            )
            fc_parts.append(f"{cur_v}[vcard{ci}]overlay=x='{cx}':y='{cy}':enable='between(t,{cs:.3f},{ce:.3f})':eof_action=pass[vc{ci}]")
            cur_v = f"[vc{ci}]"

        # Composite rich Library Composition Models (floating-media, editorial-card, stacked-cards, visual-storytelling, split-composition)
        for csi, st in enumerate(comp_stages):
            kind = st[0]
            if kind == "overlay_png":
                _, c_idx, cs, cd, anim_in, anim_out, anim_dur, anim_int, tx, ty = st
                ce = cs + cd
                fd_in = 0.05 if anim_in == "none" else min(0.45, max(0.18, anim_dur))
                fd_out = 0.05 if anim_out == "none" else min(0.45, max(0.18, anim_dur))
                ox, oy = motion_overlay_expr(anim_in, anim_out, anim_dur, anim_int, cs, ce, tx, ty, w_even, h_even)
                fc_parts.append(
                    f"[{c_idx}:v]trim=duration={cd:.3f},format=rgba,"
                    f"fade=t=in:st=0:d={fd_in:.2f}:alpha=1,fade=t=out:st={max(0.1, cd - fd_out):.3f}:d={fd_out:.2f}:alpha=1,"
                    f"setpts=PTS-STARTPTS+{cs:.3f}/TB[vcmp{csi}]"
                )
                fc_parts.append(f"{cur_v}[vcmp{csi}]overlay=x='{ox}':y='{oy}':enable='between(t,{cs:.3f},{ce:.3f})':eof_action=pass[vcmpout{csi}]")
                cur_v = f"[vcmpout{csi}]"
            elif kind == "floating":
                _, m_idx, is_img, bw, bh, rad, cs, cd, anim_in, anim_out, anim_dur, anim_int, tx, ty = st
                ce = cs + cd
                fd_in = 0.05 if anim_in == "none" else min(0.45, max(0.18, anim_dur))
                fd_out = 0.05 if anim_out == "none" else min(0.45, max(0.18, anim_dur))
                rmask = ensure_rounded_mask(Path(out_path).parent / f"cmask_{bw}x{bh}_r{rad}.png", bw, bh, radius=rad)
                temp_artifacts.append(rmask)
                rm_idx = next_in_idx
                next_in_idx += 1
                extra_inputs += ["-loop", "1", "-i", str(rmask)]
                ox, oy = motion_overlay_expr(anim_in, anim_out, anim_dur, anim_int, cs, ce, tx, ty, w_even, h_even)
                fc_parts.append(f"[{rm_idx}:v]trim=duration={cd:.3f},setpts=PTS-STARTPTS[crm{csi}]")
                fc_parts.append(
                    f"[{m_idx}:v]trim=start=0:end={cd:.3f},setpts=PTS-STARTPTS,"
                    f"scale={bw}:{bh}:force_original_aspect_ratio=increase:flags={scale_flags},crop={bw}:{bh},format=rgba[cflt{csi}]"
                )
                fc_parts.append(
                    f"[cflt{csi}][crm{csi}]alphamerge=shortest=1,"
                    f"fade=t=in:st=0:d={fd_in:.2f}:alpha=1,fade=t=out:st={max(0.1, cd - fd_out):.3f}:d={fd_out:.2f}:alpha=1,"
                    f"setpts=PTS-STARTPTS+{cs:.3f}/TB,setsar=1[cflta{csi}]"
                )
                fc_parts.append(f"{cur_v}[cflta{csi}]overlay=x='{ox}':y='{oy}':enable='between(t,{cs:.3f},{ce:.3f})':eof_action=pass[vcmpout{csi}]")
                cur_v = f"[vcmpout{csi}]"
            elif kind == "split":
                _, m_idx, is_img, orient, ratio, gap, rad, acc_hex, hl_pane, cs, cd, anim_in, anim_out, anim_dur = st
                ce = cs + cd
                ratio = max(30.0, min(70.0, ratio))
                gap = max(0, min(28, gap))
                is_horiz = (orient == "horizontal")
                if is_horiz:
                    pane_a_w = int((w_even - gap * 3) * (ratio / 100.0))
                    pane_a_w -= pane_a_w % 2
                    pane_b_w = max(120, w_even - gap * 3 - pane_a_w)
                    pane_b_w -= pane_b_w % 2
                    pane_h = h_even - gap * 2
                    pane_h -= pane_h % 2
                    ax, ay, aw, ah = gap, gap, pane_a_w, pane_h
                    bx, by, bw, bh = gap * 2 + pane_a_w, gap, pane_b_w, pane_h
                else:
                    pane_a_h = int((h_even - gap * 3) * (ratio / 100.0))
                    pane_a_h -= pane_a_h % 2
                    pane_b_h = max(160, h_even - gap * 3 - pane_a_h)
                    pane_b_h -= pane_b_h % 2
                    pane_w = w_even - gap * 2
                    pane_w -= pane_w % 2
                    ax, ay, aw, ah = gap, gap, pane_w, pane_a_h
                    bx, by, bw, bh = gap, gap * 2 + pane_a_h, pane_w, pane_b_h

                mask_a = ensure_rounded_mask(Path(out_path).parent / f"spmask_{aw}x{ah}_r{rad}.png", aw, ah, radius=rad)
                mask_b = ensure_rounded_mask(Path(out_path).parent / f"spmask_{bw}x{bh}_r{rad}.png", bw, bh, radius=rad)
                temp_artifacts.extend([mask_a, mask_b])
                ma_idx = next_in_idx; next_in_idx += 1; extra_inputs += ["-loop", "1", "-i", str(mask_a)]
                mb_idx = next_in_idx; next_in_idx += 1; extra_inputs += ["-loop", "1", "-i", str(mask_b)]

                fd = min(0.4, max(0.18, anim_dur))
                fc_parts.append(f"{cur_v}split=2[splbg{csi}][splspk{csi}]")
                fc_parts.append(f"[{ma_idx}:v]trim=duration={cd:.3f},setpts=PTS-STARTPTS[spma{csi}]")
                fc_parts.append(f"[{mb_idx}:v]trim=duration={cd:.3f},setpts=PTS-STARTPTS[spmb{csi}]")
                fc_parts.append(
                    f"[splspk{csi}]trim=start={cs:.3f}:end={ce:.3f},setpts=PTS-STARTPTS,"
                    f"scale={bw}:{bh}:force_original_aspect_ratio=increase:flags={scale_flags},crop={bw}:{bh}:(iw-ow)/2:(ih-oh)*0.20,format=rgba[spspkraw{csi}]"
                )
                fc_parts.append(
                    f"[spspkraw{csi}][spmb{csi}]alphamerge=shortest=1,"
                    f"fade=t=in:st=0:d={fd:.2f}:alpha=1,fade=t=out:st={max(0.1, cd-fd):.3f}:d={fd:.2f}:alpha=1,"
                    f"setpts=PTS-STARTPTS+{cs:.3f}/TB,setsar=1[spspka{csi}]"
                )
                fc_parts.append(
                    f"[{m_idx}:v]trim=start=0:end={cd:.3f},setpts=PTS-STARTPTS,"
                    f"scale={aw}:{ah}:force_original_aspect_ratio=increase:flags={scale_flags},crop={aw}:{ah},format=rgba[spmedraw{csi}]"
                )
                fc_parts.append(
                    f"[spmedraw{csi}][spma{csi}]alphamerge=shortest=1,"
                    f"fade=t=in:st=0:d={fd:.2f}:alpha=1,fade=t=out:st={max(0.1, cd-fd):.3f}:d={fd:.2f}:alpha=1,"
                    f"setpts=PTS-STARTPTS+{cs:.3f}/TB,setsar=1[spmeda{csi}]"
                )
                fc_parts.append(f"[splbg{csi}]drawbox=x=0:y=0:w={w_even}:h={h_even}:color=0x090d11@0.92:t=fill:enable='between(t,{cs:.3f},{ce:.3f})'[spdark{csi}]")
                fc_parts.append(f"[spdark{csi}][spspka{csi}]overlay=x={bx}:y={by}:enable='between(t,{cs:.3f},{ce:.3f})':eof_action=pass[spstep1_{csi}]")
                fc_parts.append(f"[spstep1_{csi}][spmeda{csi}]overlay=x={ax}:y={ay}:enable='between(t,{cs:.3f},{ce:.3f})':eof_action=pass[spstep2_{csi}]")
                if hl_pane in ("a", "b"):
                    hx, hy, hw_b, hh_b = (ax, ay, aw, ah) if hl_pane == "a" else (bx, by, bw, bh)
                    hcol = "0x" + (acc_hex.strip().lstrip("#") or "22C55E")
                    fc_parts.append(f"[spstep2_{csi}]drawbox=x={hx}:y={hy}:w={hw_b}:h={hh_b}:color={hcol}@0.88:t=4:enable='between(t,{cs:.3f},{ce:.3f})'[vcmpout{csi}]")
                else:
                    fc_parts.append(f"[spstep2_{csi}]null[vcmpout{csi}]")
                cur_v = f"[vcmpout{csi}]"

        fc_parts.append(f"{cur_v}subtitles='{ass_escaped}':fontsdir='{fonts_escaped}'[vout]")

        if not has_src_audio:
            cur_a = None
        elif af_chain:
            fc_parts.append(f"{a_chain}{af_chain}[aclean]")
            cur_a = "[aclean]"
        else:
            cur_a = "0:a?" if a_chain == "[0:a]" else a_chain

        fc = ";".join(fc_parts)
        map_args = ["-filter_complex", fc, "-map", "[vout]"] + (["-map", cur_a] if cur_a else [])
    else:
        sub_filter = f"{scale_base}{zoom_filter},subtitles='{ass_escaped}':fontsdir='{fonts_escaped}'"
        map_args = ["-vf", sub_filter] + (["-af", af_chain] if af_chain else []) + ["-map", "0:v:0"] + (["-map", "0:a?"] if has_src_audio else [])

    base_cmd = [ffmpeg, "-y", "-i", str(src_path)] + extra_inputs + map_args + [
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"
    ]

    try:
        if hw.get("nvenc_ready"):
            nv_cmd = base_cmd + ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "18", str(out_path)]
            r = subprocess.run(nv_cmd, capture_output=True, text=True)
            if r.returncode == 0 and Path(out_path).exists():
                return

        if low_ram:
            cpu_cmd = base_cmd + [
                "-filter_threads", "1", "-filter_complex_threads", "1",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "21",
                "-maxrate", "4500k", "-bufsize", "2M",
                "-rc-lookahead", "6", "-refs", "1", "-bf", "0",
                "-threads", "1", str(out_path)
            ]
        else:
            cpu_preset = "fast" if hw.get("cpu_cores", 4) >= 4 else "veryfast"
            cpu_cmd = base_cmd + [
                "-c:v", "libx264", "-preset", cpu_preset, "-crf", "17",
                "-threads", str(hw.get("cpu_threads", 0)), str(out_path)
            ]
        r = subprocess.run(cpu_cmd, capture_output=True, text=True, timeout=360)
        if r.returncode != 0:
            raise RuntimeError(f"Erro no FFmpeg: {(r.stderr or '')[-400:]}")
    finally:
        for tp in temp_artifacts:
            try:
                Path(tp).unlink(missing_ok=True)
            except Exception:
                pass
