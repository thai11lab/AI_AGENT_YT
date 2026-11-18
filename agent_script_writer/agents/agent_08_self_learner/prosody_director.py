"""Vocal Prosody, Breathing Cadence & Intensity Curve Director (Agent 08).
Biến một câu lời bình thông thường thành một 'Bản Phổ Giọng Đọc' (Vocal Performance Score) có:
1. Hơi thở & Nhịp ngắt nghỉ tự nhiên (Micro-pauses `...`, Dramatic Caesura `—`, Deep Breath `[hơi thở sâu / 0.45s]`).
2. Đường cong Cường độ Giọng (Dynamic Intensity Curve: LOW_WHISPER 🔉 -> MID_NARRATIVE 🎙️ -> HIGH_ACCENT 🔥 -> DROP_CHILL ❄️).
3. Từ khóa Nhấn Trọng Âm (Stress / Accent Words) đồng bộ với thời điểm nổ SFX và nhịp nghỉ sau cảnh (`pause_after_sec`).
"""
import re
from typing import Dict, List

PIVOT_CONJUNCTIONS = (
    "thế nhưng",
    "nhưng thực tế",
    "nhưng khi",
    "nhưng",
    "tuy nhiên",
    "kỳ lạ thay",
    "khoan đã",
    "ngược lại",
    "except",
    "but when",
    "in reality",
    "wait",
    "yet",
    "however",
    "until",
)

LOW_DROP_CUES = (
    "im lặng",
    "ngừng đập",
    "đã chết",
    "biến mất",
    "không một ai",
    "bí mật",
    "dead silence",
    "flatlined",
    "nobody",
    "never",
    "disappeared",
    "quietly",
)

HIGH_SURGE_CUES = (
    "bùng nổ",
    "sụp đổ",
    "cơn bão",
    "chấn động",
    "không thể",
    "lật ngược",
    "erupted",
    "collapses",
    "exploded",
    "impossible",
    "smoking gun",
    "shocking",
)


def inject_breathing_and_prosody_markers(voiceover_text: str) -> str:
    """Tự động tinh chỉnh dấu câu để tạo nhịp lấy hơi (`...`) và nhịp ngắt kịch tính (`—`) đúng chỗ lật ý."""
    t = re.sub(r"\s+", " ", voiceover_text.strip())
    if not t:
        return t

    # Nếu chưa có dấu `...` hoặc `—`, tự động chèn nhịp lấy hơi/ngắt giọng trước từ chuyển ý mạnh
    if "—" not in t and "..." not in t:
        for kw in (
            "Thế nhưng",
            "Nhưng thực tế",
            "Nhưng khi",
            "Khoan đã",
            "Except",
            "In reality",
            "Wait",
            "But when",
        ):
            pattern = rf"\.\s+({re.escape(kw)})\b"
            if re.search(pattern, t):
                t = re.sub(pattern, r". — \1", t, count=1)
                break

        # Chèn nhịp ngừng lấy hơi nhẹ `...` trước mệnh đề bất ngờ ở vế sau
        for sub_kw in ("lại vừa", "bỗng nhiên", "hoàn toàn sụp đổ", "suddenly", "just erupted", "falls apart"):
            if sub_kw in t.lower() and "..." not in t:
                t = re.sub(rf"\s+({re.escape(sub_kw)})\b", r"... \1", t, count=1, flags=re.IGNORECASE)
                break

    return t


def analyze_scene_prosody(voiceover_text: str, act_phase: str = "HOOK", pause_after_sec: float = 0.35) -> Dict:
    """Phân tích một câu lời bình thành các Chặng Hơi Thở (Breath Segments) kèm Cường độ (Intensity), Tốc độ (Rate) và Tông giọng (Pitch)."""
    clean_vo = inject_breathing_and_prosody_markers(voiceover_text)

    # Tách câu thành các chặng hơi thở theo dấu chấm, chấm hỏi, gạch ngang dài (—), hoặc dấu ba chấm (...)
    raw_chunks = re.split(r"(\.\.\.|—|[.!?])", clean_vo)
    segments: List[Dict] = []
    buf = ""

    for token in raw_chunks:
        if not token:
            continue
        if token in ("...", "—", ".", "!", "?"):
            buf += token
            text_seg = buf.strip()
            if len(text_seg) > 1:
                segments.append(_classify_breath_segment(text_seg, token, len(segments), act_phase))
            buf = ""
        else:
            buf += token

    if buf.strip():
        segments.append(_classify_breath_segment(buf.strip(), ".", len(segments), act_phase))

    # Gợi ý pause_after_sec tối ưu theo kết câu
    recommended_pause = pause_after_sec
    if clean_vo.endswith("?") or any(k in clean_vo.lower() for k in ("sụp đổ", "bùng nổ", "đã chết", "erupted", "collapses", "already knew")):
        recommended_pause = max(pause_after_sec, 0.65)
    elif "..." in clean_vo or "—" in clean_vo:
        recommended_pause = max(pause_after_sec, 0.45)

    # Chuỗi biểu diễn trực quan Đường cong Cường độ & Hơi thở
    arc_labels = [s["intensity_badge"] for s in segments]
    annotated_lines = []
    for s in segments:
        annotated_lines.append(
            f"{s['intensity_badge']} [{s['rate']} | {s['pitch']}] \"{s['text']}\" ➔ 🫁 {s['breath_cue']}"
        )

    return {
        "polished_vo": clean_vo,
        "segments": segments,
        "intensity_arc": " ➔ ".join(arc_labels),
        "recommended_pause_after_sec": round(recommended_pause, 2),
        "annotated_performance_script": "\n      ".join(annotated_lines),
    }


def _classify_breath_segment(seg_text: str, delimiter: str, seg_idx: int, act_phase: str) -> Dict:
    low = seg_text.lower()
    wc = len(seg_text.split())

    has_pivot = any(p in low for p in PIVOT_CONJUNCTIONS)
    has_low = any(c in low for c in LOW_DROP_CUES)
    has_high = any(c in low for c in HIGH_SURGE_CUES) or delimiter in ("?", "!")

    if has_high or (has_pivot and delimiter in ("...", "—", "?")):
        intensity = "HIGH_SURGE"
        badge = "🔥 CAO TRÀO (Nhấn mạnh)"
        rate = "+6% tốc độ"
        pitch = "+3Hz căng"
        db_shift = "+2.5dB"
    elif has_low or (wc <= 7 and seg_idx > 0):
        intensity = "LOW_DROP"
        badge = "❄️ HẠ TRẦM (Lạnh & Chậm)"
        rate = "-12% tốc độ"
        pitch = "-5Hz trầm"
        db_shift = "-1.5dB"
    elif seg_idx == 0:
        intensity = "MID_ANCHOR"
        badge = "🎙️ DẪN CHUYỆN (Chắc nhịp)"
        rate = "Chuẩn 0%"
        pitch = "-2Hz ấm"
        db_shift = "0.0dB"
    else:
        intensity = "RISING_TENSION"
        badge = "⚡ ĐẨY NHỊP (Tăng lực)"
        rate = "+4% tốc độ"
        pitch = "+1Hz"
        db_shift = "+1.0dB"

    if delimiter == "...":
        breath = "Ngừng lửng lấy hơi nhẹ (0.35s)"
    elif delimiter == "—":
        breath = "Ngắt nhịp đột ngột tạo kịch tính (0.25s)"
    elif delimiter == "?":
        breath = "Ngừng treo câu hỏi xoáy vào người nghe (0.55s)"
    elif intensity in ("HIGH_SURGE", "LOW_DROP"):
        breath = "Hít hơi sâu nén cảm xúc (0.50s)"
    else:
        breath = "Lấy hơi chuyển câu tự nhiên (0.30s)"

    # Tìm từ khóa đinh trong chặng để in hoa nhấn trọng âm
    words = seg_text.split()
    stress_word = words[-1].strip(".,!?—") if words else ""
    for w in words:
        w_clean = w.lower().strip(".,!?—")
        if w_clean in ("gamma", "chết", "sụp", "bùng", "ngừng", "mâu", "thực", "flatlined", "erupted", "lie", "suicide", "trap"):
            stress_word = w.strip(".,!?—")
            break

    return {
        "text": seg_text,
        "intensity": intensity,
        "intensity_badge": badge,
        "rate": rate,
        "pitch": pitch,
        "db_shift": db_shift,
        "breath_cue": breath,
        "stress_word": stress_word,
    }
