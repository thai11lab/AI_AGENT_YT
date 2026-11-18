"""Node 1: lấy transcript + bình luận của video đối thủ.
Thứ tự ưu tiên transcript: (1) file dán tay  (2) phụ đề YouTube qua yt-dlp  (3) Groq Whisper (audio ≤ ~24MB).
"""
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from core.config import get_key


def _wpm(segments: List[Dict]) -> Dict[str, float]:
    """segments: [{start, text}] -> WPM 60s đầu và phần thân (ước tính từ mốc phụ đề)."""
    def wpm(segs, dur):
        words = sum(len(s["text"].split()) for s in segs)
        return round(words / dur * 60, 1) if dur > 0 else 0.0
    hook = [s for s in segments if s["start"] < 60]
    body = [s for s in segments if s["start"] >= 60]
    total = (segments[-1]["start"] if segments else 0)
    return {"hook_60s_wpm": wpm(hook, min(60, total)), "body_wpm": wpm(body, max(total - 60, 0))}


def _pick_caption(info: Dict, prefer=("en", "vi")) -> Optional[str]:
    for pool in ("subtitles", "automatic_captions"):
        caps = info.get(pool) or {}
        for lang in list(prefer) + [k for k in caps if k.split("-")[0] in prefer]:
            for fmt in caps.get(lang, []):
                if fmt.get("ext") == "json3":
                    return fmt["url"]
    return None


def fetch_video(url: str, max_comments: int = 100) -> Dict:
    """Trả {title, segments, comments, source}. segments có thể rỗng nếu không có phụ đề."""
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "no_warnings": True,
            "getcomments": max_comments > 0,
            "extractor_args": {"youtube": {"max_comments": [str(max_comments), "0", "0", "0"]}}}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    segments: List[Dict] = []
    cap_url = _pick_caption(info)
    if cap_url:
        data = httpx.get(cap_url, timeout=30).json()
        for ev in data.get("events", []):
            txt = "".join(s.get("utf8", "") for s in ev.get("segs", []) if s.get("utf8")).strip()
            if txt:
                segments.append({"start": ev.get("tStartMs", 0) / 1000, "text": txt.replace("\n", " ")})
    comments = [c.get("text", "") for c in (info.get("comments") or [])][:max_comments]
    return {"title": info.get("title", ""), "duration": info.get("duration", 0),
            "segments": segments, "comments": comments,
            "source": "youtube_captions" if segments else "none", "url": url}


def transcribe_with_groq(url: str) -> List[Dict]:
    """Dự phòng: tải audio rồi gửi Groq Whisper. Lỗi rõ ràng nếu file quá lớn."""
    import yt_dlp
    from groq import Groq
    with tempfile.TemporaryDirectory() as td:
        opts = {"quiet": True, "format": "bestaudio[ext=m4a]/bestaudio", "outtmpl": f"{td}/a.%(ext)s"}
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        f = next(Path(td).glob("a.*"))
        if f.stat().st_size > 24 * 1024 * 1024:
            raise RuntimeError("Audio > 24MB: cần cắt nhỏ bằng ffmpeg hoặc dùng --transcript file dán tay.")
        r = Groq(api_key=get_key("GROQ_API_KEY")).audio.transcriptions.create(
            file=(f.name, f.read_bytes()), model="whisper-large-v3-turbo",
            response_format="verbose_json")
        return [{"start": s["start"], "text": s["text"].strip()} for s in r.segments]


def load_manual_transcript(path: str) -> List[Dict]:
    """File văn bản thuần. Không có mốc thời gian nên WPM = 0."""
    text = Path(path).read_text(encoding="utf-8")
    return [{"start": 0.0, "text": text}]


def build_input(url: str, manual_path: Optional[str] = None, max_comments: int = 100) -> Dict:
    if manual_path:
        segs = load_manual_transcript(manual_path)
        video = {"title": "(manual)", "segments": segs, "comments": [], "source": "manual", "url": url}
    else:
        video = fetch_video(url, max_comments)
        if not video["segments"]:
            video["segments"] = transcribe_with_groq(url)
            video["source"] = "groq_whisper"
    video["transcript"] = " ".join(s["text"] for s in video["segments"])
    video.update(_wpm(video["segments"]) if video["source"] != "manual" else
                 {"hook_60s_wpm": 0.0, "body_wpm": 0.0})
    return video

