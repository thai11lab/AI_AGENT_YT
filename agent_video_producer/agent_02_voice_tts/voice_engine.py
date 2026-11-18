"""Agent 1: Emotional Voice & Zero-Shot Voice Cloning Studio (agent_voice).
Hỗ trợ theo thứ tự ưu tiên chất lượng cao nhất:
1. Kokoro-82M TTS (`kokoro` / `kokoro_onnx` / Kokoro FastAPI Server `localhost:8880` / Fal.ai `kokoro`) — Hỗ trợ chia tách từng chặng hơi thở (Clause-by-Clause Prosody Synthesis) với tốc độ & cường độ lên xuống theo cảm xúc.
2. Chatterbox TTS (Resemble AI) — Clone giọng từ 5-10s mẫu + thanh trượt cảm xúc (Emotion Exaggeration) + tiếng thở tự nhiên.
3. OpenAI gpt-4o-mini-tts — Đạo diễn cảm xúc bằng prompt (emotional instructions).
4. Edge-TTS Neural / Local Studio Fallback — Kèm bộ lọc âm thanh phòng thu FFmpeg (Tube Warmth + Sub-bass + Breath Pauses).
"""
import math
import re
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from shared.channels import ChannelPersona
from shared.contracts import VoiceSceneOutput, WordTiming
from shared.env import get_env_key


def _inject_breathing_cadence(text: str) -> str:
    """Chèn nhịp nghỉ lấy hơi tự nhiên trước các mệnh đề lật ngược để phá bỏ nhịp đọc đều đều của AI."""
    t = text.strip()
    t = re.sub(
        r",\s+(but|yet|except|until|in reality|nhưng|thế nhưng|tuy nhiên|ngoại trừ|ngược lại)\b",
        r" ... \1",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\.\s+(Thế nhưng|Nhưng thực tế|Khoan đã|Except|In reality|Wait)\b",
        r". ... \1",
        t,
    )
    return t


def _read_wav_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return round(frames / float(rate), 3) if rate else 5.0
    except Exception:
        return 5.0


def _ffprobe_duration(path: Path) -> float:
    if path.suffix.lower() == ".wav":
        d = _read_wav_duration(path)
        if d > 0.1:
            return d
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            out = subprocess.check_output(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                timeout=10,
            ).decode().strip()
            return round(float(out), 3)
        except Exception:
            pass
    return 5.0


def _master_voice_ffmpeg(raw_audio: Path, final_wav: Path, persona: ChannelPersona, voiceover_text: str = "") -> None:
    """Áp dụng chuỗi lọc âm thanh phòng thu + Dynamic Vocal Intensity Envelope (Lên bổng xuống trầm theo ngữ nghĩa câu)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        shutil.copyfile(raw_audio, final_wav)
        return

    low = (voiceover_text or "").lower()
    # Tự động điều chỉnh lực nén, độ dày ngực (95Hz) và độ sáng (3200Hz) theo cảm xúc câu
    if any(k in low for k in ("bùng nổ", "sụp đổ", "cơn bão", "erupted", "collapses", "exploded", "?")):
        # Câu Cao trào / Chất vấn: Tăng độ sắc nét 3.2kHz (+3.2dB) & đẩy gain nhẹ (+1.5dB)
        presence_gain = "3.2"
        chest_gain = "2.8"
        post_vol = ",volume=1.5dB"
        pad_dur = "0.28"
    elif any(k in low for k in ("im lặng", "ngừng đập", "đã chết", "bí mật", "flatlined", "dead silence", "nobody")):
        # Câu Hạ trầm / Lạnh người: Tăng độ trầm ấm ngực 95Hz (+4.5dB), hạ nhẹ độ gắt để tạo cảm giác thì thầm sát mic
        presence_gain = "1.2"
        chest_gain = "4.5"
        post_vol = ",volume=-0.5dB"
        pad_dur = "0.42"
    else:
        presence_gain = "2.0"
        chest_gain = "3.2"
        post_vol = ""
        pad_dur = "0.24"

    # Không dùng silenceremove gắt (-42dB) ở đầu/cuối để tránh cắt mất âm tiết nhẹ hoặc phụ âm cuối câu
    af_chain = (
        "highpass=f=65,"
        f"equalizer=f=95:width_type=o:width=1.2:g={chest_gain},"
        f"equalizer=f=3200:width_type=o:width=1.5:g={presence_gain},"
        f"acompressor=threshold=-18dB:ratio=3.0:attack=10:release=160{post_vol},"
        f"apad=pad_dur={pad_dur}"
    )
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(raw_audio), "-af", af_chain, "-ar", "24000", "-ac", "1", str(final_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except Exception:
        shutil.copyfile(raw_audio, final_wav)


def _synth_fallback_wav(text: str, out_wav: Path, sample_rate: int = 24000) -> float:
    """Tạo file WAV giọng trầm mô phỏng nhịp đọc theo âm tiết (khi chạy hoàn toàn offline trong sandbox/test)."""
    words = text.split()
    dur = max(2.2, round(len(words) / 2.5, 2))
    n_samples = int(dur * sample_rate)
    buf = bytearray()
    for i in range(n_samples):
        t = i / sample_rate
        # Nhịp âm tiết tự nhiên (syllable envelope ~ 3.5 Hz)
        syl = max(0.0, math.sin(2 * math.pi * 3.4 * t)) ** 1.6
        # Tần số cơ bản giọng nam trầm (105Hz + ngữ điệu nhẹ)
        f0 = 105.0 - 12.0 * (t / dur) + 4.0 * math.sin(2 * math.pi * 1.1 * t)
        val = (
            0.55 * math.sin(2 * math.pi * f0 * t)
            + 0.25 * math.sin(2 * math.pi * (f0 * 2) * t)
            + 0.12 * math.sin(2 * math.pi * (f0 * 3) * t)
        ) * syl * 0.25
        sample = max(-32767, min(32767, int(val * 32767)))
        buf.extend(struct.pack("<h", sample))

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(buf))
    return dur


_KOKORO_PIPELINE_CACHE = {}
_OMNIVOICE_MODEL_CACHE = {}
_VIENEU_CACHE = {}


def _split_into_prosody_clauses(text: str) -> List[Dict]:
    """Tách câu lời bình thành các chặng hơi thở (clauses) kèm tốc độ đọc (speed), độ nghỉ lấy hơi (pause_sec) và gain cường độ."""
    t = _inject_breathing_cadence(text)
    raw_parts = re.split(r"(\.\.\.|—|[.!?])", t)
    clauses: List[Dict] = []
    buf = ""
    for tok in raw_parts:
        if not tok:
            continue
        if tok in ("...", "—", ".", "!", "?"):
            buf += tok
            seg = buf.strip()
            if len(seg) > 1:
                clauses.append(_score_clause_prosody(seg, tok, len(clauses)))
            buf = ""
        else:
            buf += tok
    if buf.strip():
        clauses.append(_score_clause_prosody(buf.strip(), ".", len(clauses)))
    return clauses


def _score_clause_prosody(seg: str, delim: str, idx: int) -> Dict:
    low = seg.lower()
    wc = len(seg.split())
    if any(k in low for k in ("erupted", "collapses", "exploded", "impossible", "suicide", "bùng nổ", "sụp đổ", "cơn bão")) or delim in ("?", "!"):
        # Cao trào: đọc nhấn mạnh, tăng nhẹ tốc độ +5%, tăng âm lượng +18%
        speed = 1.05
        gain = 1.18
        pause_sec = 0.48 if delim == "?" else 0.38
    elif any(k in low for k in ("flatlined", "dead silence", "nobody", "never", "disappeared", "already knew", "im lặng", "ngừng đập", "đã chết")) or (wc <= 6 and idx > 0):
        # Hạ trầm lạnh người: đọc chậm lại -12% để từng từ thấm vào tai người nghe
        speed = 0.88
        gain = 0.94
        pause_sec = 0.45
    elif delim in ("...", "—"):
        # Ngắt nhịp lấy hơi trước cú lật
        speed = 0.95
        gain = 1.05
        pause_sec = 0.35
    else:
        speed = 0.98
        gain = 1.0
        pause_sec = 0.26
    return {"text": seg, "speed": speed, "gain": gain, "pause_sec": pause_sec}


def _find_local_kokoro_models() -> tuple[Optional[Path], Optional[Path]]:
    """Tìm file kokoro-v1.0.onnx / kokoro-v0_19.onnx và voices-v1.0.bin trên máy người dùng."""
    env_model = get_env_key("KOKORO_MODEL_PATH")
    env_voices = get_env_key("KOKORO_VOICES_PATH")
    if env_model and env_voices and Path(env_model).exists() and Path(env_voices).exists():
        return Path(env_model), Path(env_voices)

    home = Path.home()
    workspace_root = Path(__file__).resolve().parents[2]
    candidate_dirs = [
        workspace_root,
        workspace_root / "models",
        workspace_root / "kokoro",
        home / ".cache" / "kokoro",
        home / ".cache" / "huggingface",
        home / "Models",
        home / "Downloads",
    ]
    for d in candidate_dirs:
        if not d.exists():
            continue
        try:
            onnx_files = list(d.glob("*kokoro*.onnx"))
            voice_files = list(d.glob("*voices*.bin")) + list(d.glob("*voices*.json")) + list(d.glob("*voices*.npz"))
            if onnx_files and voice_files:
                return onnx_files[0], voice_files[0]
        except Exception:
            continue
    return None, None


def _write_pcm16_wav(samples: List[int], out_wav: Path, sample_rate: int = 24000) -> None:
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)


def _call_kokoro_tts(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Gọi Kokoro-82M TTS với cơ chế Clause-by-Clause Prosody (điều tiết hơi thở ngắt nghỉ & tốc độ lên xuống từng vế câu).
    Hỗ trợ 4 chế độ cài đặt Kokoro của người dùng:
    1. Thư viện Python `kokoro` (KPipeline chính thức của Hexgrad).
    2. Thư viện `kokoro_onnx` (chạy ONNX siêu tốc trên Mac M4).
    3. Kokoro FastAPI Server local (`http://localhost:8880/v1/audio/speech` hoặc `KOKORO_API_URL`).
    4. Kokoro Cloud qua Fal.ai (`fal-ai/kokoro`).
    """
    clauses = _split_into_prosody_clauses(text)
    if not clauses:
        return False
    raw_vid = getattr(persona, "kokoro_voice", "") or "am_adam"
    # Khóa cứng 100% giọng Nam trầm (nếu lỡ truyền af_* hoặc bf_* sẽ tự chuyển sang am_adam)
    voice_id = "am_adam" if raw_vid.startswith(("af_", "bf_")) else raw_vid
    sample_rate = 24000

    # --- CHẾ ĐỘ 1: Thư viện `kokoro` (Hexgrad KPipeline) ---
    try:
        from kokoro import KPipeline  # type: ignore

        lang_code = getattr(persona, "kokoro_lang_code", "") or ("b" if voice_id.startswith("b") else "a")
        if lang_code not in _KOKORO_PIPELINE_CACHE:
            _KOKORO_PIPELINE_CACHE[lang_code] = KPipeline(lang_code=lang_code)
        pipe = _KOKORO_PIPELINE_CACHE[lang_code]

        all_pcm: List[int] = []
        for cl in clauses:
            gen = pipe(cl["text"], voice=voice_id, speed=cl["speed"], split_pattern=r"\n+")
            for _, _, audio_arr in gen:
                arr = audio_arr.tolist() if hasattr(audio_arr, "tolist") else list(audio_arr)
                g = cl["gain"]
                all_pcm.extend(max(-32767, min(32767, int(float(x) * g * 32767))) for x in arr)
            # Chèn khoảng thở tự nhiên giữa các chặng
            all_pcm.extend([0] * int(cl["pause_sec"] * sample_rate))

        if len(all_pcm) > sample_rate:
            tmp = out_wav.with_suffix(".kokoro.raw.wav")
            _write_pcm16_wav(all_pcm, tmp, sample_rate)
            _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
            tmp.unlink(missing_ok=True)
            return True
    except Exception:
        pass

    # --- CHẾ ĐỘ 2: Thư viện `kokoro_onnx` ---
    try:
        from kokoro_onnx import Kokoro  # type: ignore

        m_path, v_path = _find_local_kokoro_models()
        if m_path and v_path:
            if "onnx" not in _KOKORO_PIPELINE_CACHE:
                _KOKORO_PIPELINE_CACHE["onnx"] = Kokoro(str(m_path), str(v_path))
            k_onnx = _KOKORO_PIPELINE_CACHE["onnx"]
            all_pcm = []
            for cl in clauses:
                samples_arr, sr = k_onnx.create(cl["text"], voice=voice_id, speed=cl["speed"], lang="en-us")
                sample_rate = int(sr)
                g = cl["gain"]
                all_pcm.extend(max(-32767, min(32767, int(float(x) * g * 32767))) for x in samples_arr)
                all_pcm.extend([0] * int(cl["pause_sec"] * sample_rate))
            if len(all_pcm) > sample_rate:
                tmp = out_wav.with_suffix(".kokoro.raw.wav")
                _write_pcm16_wav(all_pcm, tmp, sample_rate)
                _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
                tmp.unlink(missing_ok=True)
                return True
    except Exception:
        pass

    # --- CHẾ ĐỘ 3: Kokoro FastAPI Local Server (mặc định http://localhost:8880/v1/audio/speech) ---
    kokoro_url = get_env_key("KOKORO_API_URL", "http://127.0.0.1:8880/v1/audio/speech")
    try:
        with httpx.Client(timeout=3.5) as client:
            resp = client.post(
                kokoro_url,
                json={
                    "model": "kokoro",
                    "voice": voice_id,
                    "input": _inject_breathing_cadence(text),
                    "response_format": "wav",
                    "speed": 0.96,
                },
            )
            if resp.status_code == 200 and len(resp.content) > 2000:
                tmp = out_wav.with_suffix(".kokoro.raw.wav")
                tmp.write_bytes(resp.content)
                _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
                tmp.unlink(missing_ok=True)
                return True
    except Exception:
        pass

    return False


def _call_vieneu_tts(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Gọi VieNeu-TTS (chuyên biệt Tiếng Việt, chạy ONNX siêu tốc trên Mac M4) với preset Giọng Nam Miền Bắc (Minh Quân) hoặc Miền Nam."""
    if persona.market_lang != "vi":
        return False
    clauses = _split_into_prosody_clauses(text)
    if not clauses:
        return False

    try:
        from vieneu import Vieneu  # type: ignore

        if "tts" not in _VIENEU_CACHE:
            _VIENEU_CACHE["tts"] = Vieneu()
        tts = _VIENEU_CACHE["tts"]

        is_south = getattr(persona, "country_code", "").upper() == "VN_NAM"
        preset_voice = "Vĩnh" if is_south else "Minh Quân"

        all_pcm: List[int] = []
        sample_rate = 24000
        for cl in clauses:
            audio = tts.infer(cl["text"], voice=preset_voice)
            arr = audio.tolist() if hasattr(audio, "tolist") else list(audio)
            g = cl["gain"]
            all_pcm.extend(max(-32767, min(32767, int(float(x) * g * 32767))) for x in arr)
            all_pcm.extend([0] * int(cl["pause_sec"] * sample_rate))

        if len(all_pcm) > sample_rate:
            tmp = out_wav.with_suffix(".vieneu.raw.wav")
            _write_pcm16_wav(all_pcm, tmp, sample_rate)
            _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
            tmp.unlink(missing_ok=True)
            return True
    except Exception:
        pass
    return False


def _call_omnivoice_tts(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Gọi k2-fsa/OmniVoice (600+ ngôn ngữ, Zero-Shot Voice Cloning & Voice Design bằng thuộc tính giọng Nam trầm).
    Hỗ trợ:
    1. Thư viện Python `omnivoice` (chạy trên Apple Silicon MPS / CPU / CUDA với Clause-by-Clause Prosody).
    2. OmniVoice FastAPI Local Server (`http://127.0.0.1:8890/v1/audio/speech` hoặc `OMNIVOICE_API_URL`).
    """
    clauses = _split_into_prosody_clauses(text)
    if not clauses:
        return False

    lang = getattr(persona, "omnivoice_lang", "") or persona.market_lang or "en"
    style_prompt = getattr(
        persona,
        "omnivoice_style_prompt",
        "male, adult, deep baritone, investigative documentary narrator, calm and authoritative",
    )
    ref_audio = None
    if persona.voice_sample_path:
        cand = Path(persona.voice_sample_path)
        if not cand.exists():
            cand = Path(__file__).resolve().parents[1] / persona.voice_sample_path
        if cand.exists():
            ref_audio = str(cand)
    sample_rate = 24000

    # --- CHẾ ĐỘ 1: Thư viện `omnivoice` (k2-fsa/OmniVoice) ---
    try:
        from omnivoice import OmniVoice  # type: ignore
        import torch  # type: ignore

        if "model" not in _OMNIVOICE_MODEL_CACHE:
            device = "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
            _OMNIVOICE_MODEL_CACHE["model"] = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=device)
        ov_model = _OMNIVOICE_MODEL_CACHE["model"]

        # Khóa danh tính giọng nói (Speaker Identity Lock) để khi chuyển nhịp điệu không bị đổi sang giọng người khác
        speaker_key = f"speaker:{lang}:{ref_audio or style_prompt}"
        clone_prompt = _OMNIVOICE_MODEL_CACHE.get(speaker_key)
        if clone_prompt is None and ref_audio:
            clone_prompt = ov_model.create_voice_clone_prompt(ref_audio=ref_audio)
            _OMNIVOICE_MODEL_CACHE[speaker_key] = clone_prompt

        all_pcm: List[int] = []
        for idx_cl, cl in enumerate(clauses):
            kwargs = {
                "text": cl["text"],
                "language": lang,
                "speed": cl["speed"],
            }
            if clone_prompt is not None:
                kwargs["voice_clone_prompt"] = clone_prompt
            else:
                kwargs["instruct"] = style_prompt

            audios = ov_model.generate(**kwargs)
            audio_arr = audios[0] if isinstance(audios, list) and audios else audios
            arr = audio_arr.tolist() if hasattr(audio_arr, "tolist") else list(audio_arr)

            # Nếu đây là chặng đầu tiên tạo từ `instruct`, khóa ngay âm sắc đó làm Neo (Speaker Anchor) cho các chặng sau
            if clone_prompt is None and idx_cl == 0 and len(arr) >= sample_rate // 2:
                t_anchor = torch.tensor(arr, dtype=torch.float32)
                if t_anchor.ndim == 1:
                    t_anchor = t_anchor.unsqueeze(0)
                clone_prompt = ov_model.create_voice_clone_prompt(
                    ref_audio=(t_anchor, sample_rate),
                    ref_text=cl["text"],
                )
                _OMNIVOICE_MODEL_CACHE[speaker_key] = clone_prompt

            g = cl["gain"]
            all_pcm.extend(max(-32767, min(32767, int(float(x) * g * 32767))) for x in arr)
            all_pcm.extend([0] * int(cl["pause_sec"] * sample_rate))

        if len(all_pcm) > sample_rate:
            tmp = out_wav.with_suffix(".omnivoice.raw.wav")
            _write_pcm16_wav(all_pcm, tmp, sample_rate)
            _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
            tmp.unlink(missing_ok=True)
            return True
    except Exception as exc:
        print(f"  [TTS Warning] OmniVoice lỗi: {exc}", flush=True)

    # --- CHẾ ĐỘ 2: OmniVoice Local Server (`OMNIVOICE_API_URL`, mặc định http://127.0.0.1:8890/v1/audio/speech) ---
    omni_url = get_env_key("OMNIVOICE_API_URL", "http://127.0.0.1:8890/v1/audio/speech")
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(
                omni_url,
                json={
                    "model": "omnivoice",
                    "language": lang,
                    "voice": style_prompt,
                    "input": _inject_breathing_cadence(text),
                    "response_format": "wav",
                },
            )
            if resp.status_code == 200 and len(resp.content) > 2000:
                tmp = out_wav.with_suffix(".omnivoice.raw.wav")
                tmp.write_bytes(resp.content)
                _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
                tmp.unlink(missing_ok=True)
                return True
    except Exception:
        pass

    return False


def _call_chatterbox_fal(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Gọi Chatterbox TTS (Resemble AI) qua Fal.ai API — hỗ trợ Emotion Exaggeration & Zero-Shot Voice Cloning."""
    fal_key = get_env_key("FAL_API_KEY") or get_env_key("FAL_KEY")
    if not fal_key:
        return False
    payload = {
        "text": _inject_breathing_cadence(text),
        "exaggeration": persona.emotion_exaggeration,
        "cfg": 0.5,
    }
    if persona.voice_sample_path and persona.voice_sample_path.startswith("http"):
        payload["audio_url"] = persona.voice_sample_path

    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post("https://fal.run/fal-ai/chatterbox/text-to-speech", headers=headers, json=payload)
            if resp.status_code >= 400:
                return False
            data = resp.json()
            audio_url = (data.get("audio") or {}).get("url")
            if not audio_url:
                return False
            audio_bytes = client.get(audio_url).content
            tmp = out_wav.with_suffix(".raw.wav")
            tmp.write_bytes(audio_bytes)
            _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
            tmp.unlink(missing_ok=True)
            return True
    except Exception:
        return False


def _call_openai_emotional_tts(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Gọi gpt-4o-mini-tts (OpenAI hoặc 370.ai) với lệnh đạo diễn cảm xúc và nhịp thở."""
    api_key = get_env_key("OPENAI_API_KEY")
    base_url = get_env_key("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        return False
    payload = {
        "model": "gpt-4o-mini-tts",
        "voice": persona.openai_voice,
        "input": _inject_breathing_cadence(text),
        "instructions": persona.emotion_prompt,
        "response_format": "wav",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(f"{base_url.rstrip('/')}/audio/speech", headers=headers, json=payload)
            if resp.status_code >= 400:
                return False
            tmp = out_wav.with_suffix(".raw.wav")
            tmp.write_bytes(resp.content)
            _master_voice_ffmpeg(tmp, out_wav, persona, voiceover_text=text)
            tmp.unlink(missing_ok=True)
            return True
    except Exception:
        return False


def _call_edge_tts(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Gọi Microsoft Edge Neural TTS (miễn phí 100%) + lọc âm thanh phòng thu FFmpeg (có retry chống rớt WebSocket)."""
    import sys
    import time

    venv_edge = Path(sys.executable).parent / "edge-tts"
    edge_bin = str(venv_edge) if venv_edge.exists() else shutil.which("edge-tts")
    if not edge_bin:
        return False
    tmp_mp3 = out_wav.with_suffix(".tmp.mp3")
    spoken_text = _inject_breathing_cadence(text)
    last_err = ""
    for attempt in range(2):
        try:
            proc = subprocess.run(
                [
                    edge_bin,
                    "--voice",
                    persona.edge_voice,
                    f"--rate={persona.speaking_rate}",
                    f"--pitch={persona.pitch_shift}",
                    "--text",
                    spoken_text,
                    "--write-media",
                    str(tmp_mp3),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode == 0 and tmp_mp3.exists() and tmp_mp3.stat().st_size > 1000:
                _master_voice_ffmpeg(tmp_mp3, out_wav, persona, voiceover_text=text)
                tmp_mp3.unlink(missing_ok=True)
                return True
            last_err = (proc.stderr or proc.stdout or f"exit {proc.returncode}").strip()[:160]
        except Exception as exc:
            last_err = str(exc)[:160]
        tmp_mp3.unlink(missing_ok=True)
        if attempt == 0:
            time.sleep(0.8)
    if last_err:
        print(f"  [TTS Warning] Edge-TTS ({persona.edge_voice}) lỗi: {last_err}", flush=True)
    return False


def _call_macos_say(text: str, out_wav: Path, persona: ChannelPersona) -> bool:
    """Sử dụng bộ đọc giọng Nam hệ thống macOS (chỉ dùng cho tiếng Anh Daniel; tiếng Việt dùng vi-VN-NamMinhNeural)."""
    if persona.market_lang == "vi":
        return False
    say_bin = shutil.which("say")
    ffmpeg_bin = shutil.which("ffmpeg")
    if not say_bin or not ffmpeg_bin:
        return False
    tmp_aiff = out_wav.with_suffix(".tmp.aiff")
    voice_name = "Daniel"
    try:
        subprocess.run(
            [say_bin, "-v", voice_name, "-r", "155", "-o", str(tmp_aiff), text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        _master_voice_ffmpeg(tmp_aiff, out_wav, persona, voiceover_text=text)
        tmp_aiff.unlink(missing_ok=True)
        return out_wav.exists() and _ffprobe_duration(out_wav) >= 1.5
    except Exception:
        tmp_aiff.unlink(missing_ok=True)
        return False


def _compute_word_timings(text: str, duration_sec: float, audio_cues: List[dict]) -> tuple[List[WordTiming], Dict[str, float]]:
    raw_words = [w for w in text.split() if w.strip()]
    if not raw_words:
        return [], {}
    # Phân bổ thời lượng theo độ dài ký tự của từng từ để khớp nhịp nói thật
    weights = [max(2, len(w)) + (3 if w.endswith((",", ".", "?", "!", ";", ":")) else 0) for w in raw_words]
    total_w = sum(weights)
    effective_dur = max(0.5, duration_sec - 0.25)

    timings: List[WordTiming] = []
    curr = 0.05
    for w, wt in zip(raw_words, weights):
        span = (wt / total_w) * effective_dur
        timings.append(WordTiming(word=w, start_sec=round(curr, 3), end_sec=round(curr + span, 3)))
        curr += span

    trigger_map: Dict[str, float] = {}
    for cue in audio_cues:
        tw = str(cue.get("trigger_word", "")).strip().lower()
        clean_tw = re.sub(r"[^\w]", "", tw)
        matched_sec = 0.2
        for wt_item in timings:
            if re.sub(r"[^\w]", "", wt_item.word.lower()) == clean_tw:
                matched_sec = wt_item.start_sec
                break
        if clean_tw:
            trigger_map[clean_tw] = matched_sec

    return timings, trigger_map


def synthesize_scene_voice(
    scene: dict,
    out_dir: Path,
    persona: ChannelPersona,
    force_local: bool = False,
    preferred_engine: str = "auto",
) -> VoiceSceneOutput:
    """Sinh file âm thanh giọng đọc cảm xúc cho 1 cảnh.
    Định tuyến thông minh theo quốc gia/ngôn ngữ (Smart Country Routing):
    - Với Tiếng Anh (US / UK / AU / CA): Ưu tiên Kokoro-82M (`am_adam`, `bm_george`, `bm_lewis`, `am_liam`) -> OmniVoice -> Chatterbox/OpenAI -> Edge Neural.
    - Với Tiếng Việt (VN) và các ngôn ngữ ngoài hệ Kokoro: Ưu tiên OmniVoice (600+ ngôn ngữ + Zero-Shot Voice Cloning) -> Edge Neural (`vi-VN-NamMinhNeural`).
    - Nếu người dùng chỉ định `preferred_engine` ('kokoro' | 'omnivoice' | 'edge'), sẽ ép chạy đúng engine đó trước để phục vụ A/B Benchmark.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    sid = scene["scene_id"]
    vo_text = scene["voiceover_text"]
    out_wav = out_dir / f"{sid}.wav"
    pref = (preferred_engine or persona.tts_engine or "auto").lower().strip()

    engine_used = "local_studio_synth"

    # Tạo danh sách thứ tự ưu tiên engine dựa theo ngôn ngữ/quốc gia và lựa chọn của người dùng
    if pref == "omnivoice":
        order = ["omnivoice", "vieneu", "kokoro", "edge", "macos"]
    elif pref == "vieneu":
        order = ["vieneu", "omnivoice", "edge"]
    elif pref == "kokoro":
        order = ["kokoro", "omnivoice", "edge", "macos"]
    elif pref == "edge":
        order = ["edge", "vieneu", "kokoro", "omnivoice", "macos"]
    elif persona.market_lang == "vi":
        # Tiếng Việt (VN_BAC / VN_NAM): Ưu tiên VieNeu-TTS (có sẵn giọng Nam Bắc 'Minh Quân') -> OmniVoice -> Edge Neural
        order = ["vieneu", "omnivoice", "chatterbox", "openai", "edge"]
    else:
        # Tiếng Anh (US/UK/AU/CA) & JP/FR/ES: Kokoro-82M đứng số 1 về tốc độ & nhịp thở tự nhiên trên Mac M4
        order = ["kokoro", "omnivoice", "chatterbox", "openai", "edge", "macos"]

    if force_local:
        order = [e for e in order if e not in ("chatterbox", "openai")]

    matched = False
    for eng in order:
        if eng == "vieneu" and persona.market_lang == "vi" and _call_vieneu_tts(vo_text, out_wav, persona):
            v_label = "Saigon" if persona.country_code == "VN_NAM" else "MinhQuan_Hanoi"
            engine_used = f"vieneu_tts:{persona.country_code}:{v_label}"
            matched = True
            break
        elif eng == "kokoro" and persona.market_lang != "vi" and _call_kokoro_tts(vo_text, out_wav, persona):
            engine_used = f"kokoro_82m_prosody:{persona.country_code}:{persona.kokoro_voice}"
            matched = True
            break
        elif eng == "omnivoice" and _call_omnivoice_tts(vo_text, out_wav, persona):
            engine_used = f"omnivoice_600lang:{persona.country_code}:{persona.omnivoice_lang}"
            matched = True
            break
        elif eng == "chatterbox" and _call_chatterbox_fal(vo_text, out_wav, persona):
            engine_used = f"chatterbox_clone:{persona.country_code}"
            matched = True
            break
        elif eng == "openai" and _call_openai_emotional_tts(vo_text, out_wav, persona):
            engine_used = f"openai_gpt4o:{persona.country_code}:{persona.openai_voice}"
            matched = True
            break
        elif eng == "edge" and _call_edge_tts(vo_text, out_wav, persona):
            engine_used = f"edge_neural:{persona.country_code}:{persona.edge_voice}"
            matched = True
            break
        elif eng == "macos" and _call_macos_say(vo_text, out_wav, persona):
            engine_used = f"macos_studio:{persona.country_code}"
            matched = True
            break

    if not matched:
        _synth_fallback_wav(vo_text, out_wav)

    dur = _ffprobe_duration(out_wav)
    timings, trig_map = _compute_word_timings(vo_text, dur, scene.get("audio_cues", []))
    return VoiceSceneOutput(
        scene_id=sid,
        audio_path=str(out_wav),
        duration_sec=dur,
        engine_used=engine_used,
        word_timings=timings,
        trigger_timestamps=trig_map,
    )
