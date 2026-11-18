"""Real Foley & Documentary SFX Library (Agent 05).
Tham khảo chuẩn GitHub (MTG/freesound-python & Losera/soundfetch):
1. Kiểm tra thư mục Foley thật do người dùng thả vào: `agent_video_producer/assets/sfx/<CATEGORY>.wav|.mp3`
2. Nếu có `FREESOUND_API_KEY` trong `.env`: tự động tìm và tải Foley Creative-Commons thật từ Freesound APIv2 về `sfx_cache/`.
3. Fallback: Sinh âm thanh cinema lọc thông thấp êm dịu (Soft Air Whoosh, Warm Sub-Boom, Subtle UI Click).
"""
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Dict

import httpx

from shared.env import get_env_key

ASSETS_SFX_DIR = Path(__file__).resolve().parents[1] / "assets" / "sfx"

FREESOUND_QUERY_MAP: Dict[str, str] = {
    "WHOOSH": "soft cinema air whoosh transition",
    "IMPACT": "deep cinematic sub bass impact boom",
    "BOOM": "deep cinematic sub bass impact boom",
    "HEART": "low subtle heartbeat thump",
    "TICK": "soft mechanical clock tick",
    "CLICK": "subtle clean ui click",
    "DATA": "subtle clean ui click",
    "RISER": "subtle cinematic tension swell",
    "SUSPENSE": "subtle cinematic tension swell",
    "RADIO": "police radio static chatter short",
}


def _convert_to_24k_mono_wav(src: Path, dst_wav: Path, max_dur: float = 0.85) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not src.exists():
        return False
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(src),
                "-t",
                f"{max_dur:.2f}",
                "-af",
                "afade=t=in:st=0:d=0.03,afade=t=out:st=0.55:d=0.25",
                "-ar",
                "24000",
                "-ac",
                "1",
                str(dst_wav),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        return dst_wav.exists() and dst_wav.stat().st_size > 1000
    except Exception:
        return False


def _try_fetch_freesound_sfx(category: str, out_wav: Path) -> bool:
    api_key = get_env_key("FREESOUND_API_KEY")
    if not api_key:
        return False
    q = FREESOUND_QUERY_MAP.get(category.upper(), "soft cinema whoosh")
    tmp_mp3 = out_wav.with_suffix(".fs.mp3")
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            r = client.get(
                "https://freesound.org/apiv2/search/text/",
                params={
                    "query": q,
                    "filter": "duration:[0.2 TO 1.5]",
                    "fields": "id,name,previews",
                    "page_size": 3,
                    "token": api_key,
                },
            )
            if r.status_code != 200:
                return False
            for hit in r.json().get("results") or []:
                prev_url = (hit.get("previews") or {}).get("preview-hq-mp3") or (hit.get("previews") or {}).get("preview-lq-mp3")
                if prev_url:
                    tmp_mp3.write_bytes(client.get(prev_url).content)
                    if _convert_to_24k_mono_wav(tmp_mp3, out_wav):
                        tmp_mp3.unlink(missing_ok=True)
                        return True
    except Exception:
        pass
    tmp_mp3.unlink(missing_ok=True)
    return False


def resolve_sfx_wav(category: str, sfx_cache_dir: Path, sample_rate: int = 24000) -> Path:
    """Lấy file SFX thật từ assets/sfx -> Freesound APIv2 -> Soft Cinema Fallback."""
    cat = (category or "WHOOSH").upper()
    sfx_cache_dir.mkdir(parents=True, exist_ok=True)
    cached_wav = sfx_cache_dir / f"{cat}_master.wav"
    if cached_wav.exists() and cached_wav.stat().st_size > 1000:
        return cached_wav

    # 1. Kiểm tra thư mục Foley thật của người dùng (`agent_video_producer/assets/sfx/`)
    if ASSETS_SFX_DIR.exists():
        for ext in (".wav", ".mp3", ".m4a"):
            local_asset = ASSETS_SFX_DIR / f"{cat}{ext}"
            if local_asset.exists() and _convert_to_24k_mono_wav(local_asset, cached_wav):
                return cached_wav

    # 2. Nếu có FREESOUND_API_KEY -> Tải Foley thật Creative-Commons
    if _try_fetch_freesound_sfx(cat, cached_wav):
        return cached_wav

    # 3. Soft Cinema Fallback (không bao giờ chói tai)
    dur = 0.48
    n_samples = int(dur * sample_rate)
    buf = bytearray()
    prev_n = 0.0
    rng_state = 1337
    for i in range(n_samples):
        t = i / sample_rate
        fade_in = min(1.0, t / 0.04)
        env = math.exp(-5.5 * t) * fade_in

        rng_state = (1103515245 * rng_state + 12345) & 0x7FFFFFFF
        white = (rng_state / float(0x3FFFFFFF)) - 1.0
        prev_n = 0.88 * prev_n + 0.12 * white

        if "IMPACT" in cat or "BOOM" in cat:
            freq = 68.0 * math.exp(-5.0 * t) + 28.0
            val = 0.42 * math.sin(2 * math.pi * freq * t) * env
        elif "HEART" in cat:
            p1 = math.exp(-45.0 * ((t - 0.10) ** 2))
            p2 = 0.65 * math.exp(-50.0 * ((t - 0.28) ** 2))
            val = 0.38 * (p1 + p2) * math.sin(2 * math.pi * 48.0 * t)
        elif "TICK" in cat or "CLICK" in cat or "DATA" in cat:
            p = math.exp(-160.0 * ((t - 0.03) ** 2))
            val = 0.22 * p * (0.6 * math.sin(2 * math.pi * 520.0 * t) + 0.4 * prev_n)
        elif "RISER" in cat or "SUSPENSE" in cat:
            sw = math.sin(math.pi * t / dur)
            val = 0.20 * sw * (0.65 * prev_n + 0.35 * math.sin(2 * math.pi * (65.0 + 90.0 * (t / dur)) * t))
        else:
            sw = math.sin(math.pi * t / dur) ** 1.4
            val = 0.26 * sw * prev_n

        sample = max(-32767, min(32767, int(val * 32767)))
        buf.extend(struct.pack("<h", sample))

    with wave.open(str(cached_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(buf))
    return cached_wav
