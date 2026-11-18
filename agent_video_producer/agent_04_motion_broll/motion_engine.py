"""Agent 3: Live 30fps Motion Graphics, B-Roll Video & 2.5D Multi-Plane Engine (agent_motion).
Chấm dứt hoàn toàn kiểu "trình chiếu slide ảnh tĩnh zoom qua lại":
1. Nếu có PEXELS_API_KEY hoặc FAL_API_KEY (Cloud Video): Tải video chuyển động thật (.mp4) từ Pexels HD B-Roll / Wan 2.1 và phủ lớp HUD điều tra động.
2. Live 30fps Frame-by-Frame Cinema Animator (Chạy trực tiếp trên chip Apple M4, $0):
   - Vẽ biến thiên từng khung hình (30 khung hình/giây) và đẩy thẳng qua ống dẫn rawvideo vào FFmpeg:
   - Kiểu 1 (ECG / Brainwave Telemetry): Sóng điện tâm đồ & sóng não gamma chạy thực tế từng frame, đồng hồ mili-giây nhảy số liên tục, nhịp tim giảm từ 138 -> 0 BPM đúng lúc flatline, đèn cấp cứu chớp đỏ/xanh.
   - Kiểu 2 (Live Document Investigation): Tờ hồ sơ trượt vào, bút dạ quang vàng quét dần từ trái sang phải theo từng frame, dấu đỏ [CRITICAL DISCREPANCY] đóng sập xuống kèm rung chấn camera (Camera Shake) đúng lúc nổ SFX.
   - Kiểu 3 (Live Forensic Timeline & Data Counter): Sơ đồ đường dây kết nối tự vẽ tia laser đỏ giữa các nút, bộ đếm tiền/thời gian chạy số nhảy liên tục từ 0 lên cực đại, hạt bụi 3D (Bokeh/Dust) bay lơ lửng trong luồng sáng.
"""
import math
import random
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from PIL import Image, ImageDraw, ImageFont

from shared.contracts import MotionSceneOutput, VisualSceneOutput, VoiceSceneOutput
from shared.env import get_env_key


def _load_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if mono:
        candidates = [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
        ]
    elif bold:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _extract_broll_query(scene: dict) -> str:
    """Rút trích cụm từ khóa hành động/vật thể chính xác từ midground_main và voiceover_text để tìm đúng ngữ cảnh (bao gồm GTA / Gaming / Documentary)."""
    ps = scene.get("parallax_spec") or {}
    mid = str(ps.get("midground_main") or "").strip()
    vo = str(scene.get("voiceover_text") or "").lower()
    combined = f"{mid} {vo}".lower()

    # Ánh xạ ngữ cảnh chuyên biệt cho GTA / Rockstar Mysteries
    if any(k in combined for k in ("gta", "los santos", "vinewood", "rockstar", "chiliad", "vice city")):
        if "police" in combined or "chase" in combined or "heist" in combined:
            return "gta 5 gameplay police chase night los santos"
        if "power station" in combined or "abandoned" in combined or "secret" in combined:
            return "gta 5 mystery secret location gameplay"
        return "gta 5 los santos night driving cinematic gameplay"
    if any(k in combined for k in ("red dead", "rdr2", "arthur morgan")):
        return "red dead redemption 2 mystery gameplay cinematic"

    # Ánh xạ ngữ cảnh Y sinh / Điều tra
    if "flatline" in vo or "monitor" in mid.lower():
        return "hospital heart monitor ecg screen"
    if "corridor" in vo or "doctor" in mid.lower():
        return "hospital hallway doctor walking dark"
    if "certificate" in vo or "timestamp" in vo or "document" in mid.lower():
        return "medical document close up signing pen"
    if "statistics" in vo or "headlines" in vo:
        return "medical data screen monitor hospital"
    if "operating" in vo or "organ" in vo or "surgeon" in vo:
        return "operating room surgery lights hospital"
    if "brain" in vo or "eeg" in vo or "gamma" in vo or "lucid" in vo:
        return "brain scan mri neurology monitor"

    raw = f"{mid} {vo}"
    raw = re.sub(
        r"\b(shot|close-up|wide|medium|lens|35mm|gritty|somber|atmosphere|lighting|contrast|angle|documentary|cinema|shallow|depth|field|chiaroscuro|editorial|framing|photorealistic|teal|amber|grade|textures|blurred|subtle|amidst)\b",
        " ",
        raw,
        flags=re.IGNORECASE,
    )
    words = [w for w in re.findall(r"[A-Za-z]+", raw) if len(w) > 3][:4]
    return " ".join(words) if words else "cinematic night city aerial"


def _log_broll_source(out_mp4: Path, sid: str, info: dict) -> None:
    import json

    log_file = out_mp4.parent / "broll_sources.json"
    data = {}
    if log_file.exists():
        try:
            data = json.loads(log_file.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data[sid] = info
    log_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _try_fetch_broll_video(scene: dict, out_mp4: Path) -> bool:
    """Tải video B-roll đúng ngữ cảnh (1. Pixabay Stock -> 2. Pexels Stock -> 3. yt-dlp Smart Mid-Slice né Intro & Vlog)."""
    if out_mp4.exists() and out_mp4.stat().st_size > 15000:
        return True
    sid = scene.get("scene_id", "S001")
    query = _extract_broll_query(scene)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # 1. Pixabay Video API (Stock footage thuần 10-30s, không có intro, đúng ngữ cảnh 100%)
    pix_key = get_env_key("PIXABAY_API_KEY")
    if pix_key:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                r = client.get(
                    "https://pixabay.com/api/videos/",
                    params={"key": pix_key, "q": query, "per_page": 5, "safesearch": "true"},
                )
                if r.status_code == 200:
                    for hit in r.json().get("hits") or []:
                        vids = hit.get("videos") or {}
                        url = (vids.get("medium") or vids.get("small") or {}).get("url")
                        if url:
                            out_mp4.write_bytes(client.get(url).content)
                            _log_broll_source(out_mp4, sid, {"source": "pixabay", "query": query, "id": hit.get("id"), "tags": hit.get("tags")})
                            return True
        except Exception:
            pass

    # 2. Pexels Video API (nếu có key)
    pkey = get_env_key("PEXELS_API_KEY")
    if pkey:
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                r = client.get(
                    "https://api.pexels.com/videos/search",
                    headers={"Authorization": pkey},
                    params={"query": query, "per_page": 3, "orientation": "landscape"},
                )
                if r.status_code == 200:
                    for v in r.json().get("videos") or []:
                        for vf in v.get("video_files", []):
                            if vf.get("width", 0) >= 1280 and vf.get("link"):
                                out_mp4.write_bytes(client.get(vf["link"]).content)
                                _log_broll_source(out_mp4, sid, {"source": "pexels", "query": query, "url": v.get("url")})
                                return True
        except Exception:
            pass

    # 3. yt-dlp Context-Verified B-Roll Slicer (Loại bỏ vlog/podcast, chỉ lấy stock clip ngắn và cắt ở mốc 40% giữa video để né Intro)
    import sys

    venv_ytdlp = Path(sys.executable).parent / "yt-dlp"
    ytdlp_bin = str(venv_ytdlp) if venv_ytdlp.exists() else shutil.which("yt-dlp")
    if ytdlp_bin:
        search_q = f"ytsearch5:{query} stock footage b-roll no talking"
        try:
            # Bước A: Lấy metadata của 5 kết quả đầu tiên để lọc đúng clip B-roll ngắn (10s - 180s), không lấy vlog/talking head
            import json

            probe = subprocess.check_output(
                [ytdlp_bin, "--dump-json", "--no-playlist", "--flat-playlist", search_q],
                stderr=subprocess.DEVNULL,
                timeout=20,
            ).decode("utf-8", errors="ignore")

            banned_words = ("podcast", "interview", "reaction", "explained", "lecture", "vlog", "review", "news anchor", "tutorial")
            chosen_url = None
            chosen_title = ""
            start_sec = 8
            for line in probe.splitlines():
                if not line.strip():
                    continue
                info = json.loads(line)
                title = str(info.get("title") or "")
                dur = float(info.get("duration") or 30.0)
                if any(bw in title.lower() for bw in banned_words):
                    continue
                if 8.0 <= dur <= 240.0 and info.get("id"):
                    chosen_url = f"https://www.youtube.com/watch?v={info['id']}"
                    chosen_title = title
                    # Cắt ở mốc 35% thời lượng video để tránh hoàn toàn Intro mở đầu và Outro cuối bài!
                    start_sec = max(3, min(int(dur * 0.35), int(dur - 9)))
                    break

            if chosen_url:
                end_sec = start_sec + 9
                section_arg = f"*00:{start_sec // 60:02d}:{start_sec % 60:02d}-00:{end_sec // 60:02d}:{end_sec % 60:02d}"
                subprocess.run(
                    [
                        ytdlp_bin,
                        "--no-playlist",
                        "-f", "mp4[height<=720]/best[height<=720]",
                        "--download-sections", section_arg,
                        "-o", str(out_mp4),
                        chosen_url,
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=35,
                )
                if out_mp4.exists() and out_mp4.stat().st_size > 15000:
                    _log_broll_source(
                        out_mp4,
                        sid,
                        {
                            "source": "ytdlp_smart_broll",
                            "query": query,
                            "video_title": chosen_title,
                            "url": chosen_url,
                            "slice_window": section_arg,
                        },
                    )
                    return True
        except Exception:
            pass

    return False


def _choose_animation_archetype(scene: dict, idx_num: int) -> str:
    mode = scene.get("visual_mode", "")
    vo = (scene.get("voiceover_text", "") + " " + scene.get("flux_base_image_prompt", "")).lower()
    if mode == "DOCUMENT_HIGHLIGHT" or any(k in vo for k in ("certificate", "timestamp", "document", "record", "act", "referral")):
        return "LIVE_DOCUMENT"
    if mode == "KINETIC_DATA_CARD" or any(k in vo for k in ("statistics", "headlines", "incentives", "percent", "billion", "quota")):
        return "LIVE_DATA_NETWORK"
    if any(k in vo for k in ("flatline", "beeping", "emergency", "heart", "brain", "eeg", "gamma", "monitor", "hospital")):
        return "LIVE_BIOMETRIC_MONITOR" if idx_num % 2 == 1 else "LIVE_CORRIDOR_SCAN"
    return ["LIVE_BIOMETRIC_MONITOR", "LIVE_DOCUMENT", "LIVE_DATA_NETWORK", "LIVE_CORRIDOR_SCAN"][idx_num % 4]


def _draw_particles_and_scanlines(draw: ImageDraw.ImageDraw, w: int, h: int, t: float, particles: list, accent: tuple) -> None:
    # Hạt bụi 3D bay trong không gian (Depth-of-Field Floating Dust)
    for px, py, spd, sz, alpha in particles:
        cur_x = int((px + spd * 42 * t) % w)
        cur_y = int((py - spd * 28 * t) % h)
        draw.ellipse((cur_x - sz, cur_y - sz, cur_x + sz, cur_y + sz), fill=(accent[0], accent[1], accent[2], alpha))

    # Dải quét CRT / Forensic Scanline di chuyển dọc màn hình
    scan_y = int((t * 190) % h)
    draw.rectangle((0, scan_y, w, scan_y + 3), fill=(255, 255, 255, 18))


def _draw_word_by_word_subtitle(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    t: float,
    voice_out: Optional[VoiceSceneOutput],
    fallback_text: str,
    trigger_words: set,
    f_sub: ImageFont.FreeTypeFont,
    f_sub_big: ImageFont.FreeTypeFont,
) -> None:
    """Hiển thị phụ đề động từng cụm 5 từ, từ đang đọc phóng to + đổi màu Vàng/Đỏ theo thời gian thực."""
    timings = voice_out.word_timings if (voice_out and voice_out.word_timings) else []
    if not timings:
        words = fallback_text.split()
        dur = 6.0
        step = dur / max(1, len(words))
        from shared.contracts import WordTiming
        timings = [WordTiming(word=wd, start_sec=i * step, end_sec=(i + 1) * step) for i, wd in enumerate(words)]

    active_idx = 0
    for i, wt in enumerate(timings):
        if wt.start_sec <= t <= wt.end_sec + 0.15:
            active_idx = i
            break
        if t > wt.end_sec:
            active_idx = i

    chunk_size = 5
    chunk_start = (active_idx // chunk_size) * chunk_size
    chunk = timings[chunk_start : chunk_start + chunk_size]

    # Tính chiều rộng cụm từ
    items = []
    space_w = 12
    for j, wt in enumerate(chunk):
        abs_i = chunk_start + j
        is_active = abs_i == active_idx
        clean_w = re.sub(r"[^\w]", "", wt.word.lower())
        is_trig = clean_w in trigger_words
        font_use = f_sub_big if is_active else f_sub
        txt = wt.word.upper()
        bb = draw.textbbox((0, 0), txt, font=font_use)
        items.append((txt, bb[2] - bb[0], is_active, is_trig, font_use))

    total_w = sum(x[1] for x in items) + space_w * max(0, len(items) - 1)
    box_l = max(50, (w - total_w) // 2 - 26)
    box_r = min(w - 50, (w + total_w) // 2 + 26)
    box_t = h - 106
    box_b = h - 34

    draw.rounded_rectangle((box_l, box_t, box_r, box_b), radius=12, fill=(4, 7, 12, 232), outline=(255, 255, 255, 50), width=2)

    cur_x = (w - total_w) // 2
    for txt, ww, is_active, is_trig, font_use in items:
        y_pos = box_t + (11 if is_active else 16)
        if is_active and is_trig:
            color = (239, 68, 68, 255)  # Đỏ rực khi chạm từ khóa nổ SFX
        elif is_active:
            color = (251, 191, 36, 255)  # Vàng Gold cho từ đang phát âm
        elif is_trig:
            color = (253, 224, 71, 220)
        else:
            color = (241, 245, 249, 235)

        draw.text((cur_x + 2, y_pos + 2), txt, fill=(0, 0, 0, 240), font=font_use)
        draw.text((cur_x, y_pos), txt, fill=color, font=font_use)
        cur_x += ww + space_w


def _render_live_30fps_scene(
    scene: dict,
    visual: VisualSceneOutput,
    voice_out: Optional[VoiceSceneOutput],
    duration_sec: float,
    out_mp4: Path,
    fps: int = 30,
    force_local: bool = False,
) -> bool:
    """Render chuyển động đồ họa 30fps biến thiên từng frame đẩy trực tiếp qua ống dẫn FFmpeg rawvideo."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    w, h = 1280, 720
    # Làm tròn lên (+3 frames = +0.1s) để video luôn dài >= audio, tránh mất chữ cuối khi ghép cảnh
    total_frames = max(45, math.ceil(duration_sec * fps) + 3)
    sid = scene.get("scene_id", "S001")
    idx_num = int(sid[1:]) if sid[1:].isdigit() else 1
    archetype = _choose_animation_archetype(scene, idx_num)

    rng = random.Random(idx_num * 97)
    particles = [
        (rng.randint(0, w), rng.randint(0, h), rng.uniform(0.4, 1.8), rng.randint(1, 3), rng.randint(35, 110))
        for _ in range(42)
    ]

    f_hud = _load_font(16, bold=True, mono=True)
    f_title = _load_font(28, bold=True)
    f_big_num = _load_font(54, bold=True, mono=True)
    f_doc = _load_font(22, bold=True)
    f_doc_sm = _load_font(17, mono=True)
    f_sub = _load_font(26, bold=True)
    f_sub_big = _load_font(31, bold=True)

    trig_map = voice_out.trigger_timestamps if voice_out else {}
    trig_times = list(trig_map.values()) if trig_map else [duration_sec * 0.35]
    trig_words = {re.sub(r"[^\w]", "", str(c.get("trigger_word", "")).lower()) for c in scene.get("audio_cues", [])}

    # Nếu có video B-roll thật (từ yt-dlp / Pixabay / Pexels), đọc từng frame chuyển động thật làm nền!
    broll_reader = None
    broll_path = out_mp4.parent / "broll_cache" / f"{sid}_broll.mp4"
    if not force_local and _try_fetch_broll_video(scene, broll_path):
        try:
            broll_reader = subprocess.Popen(
                [
                    ffmpeg, "-stream_loop", "-1", "-i", str(broll_path),
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},eq=contrast=1.12:saturation=0.65:brightness=-0.12",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "-r", str(fps), "-",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            broll_reader = None

    # Nếu có ảnh AI thật (từ Flux/Pollinations/Fal), nạp sẵn làm lớp nền chuyển động
    bg_source: Optional[Image.Image] = None
    base_p = Path(visual.base_image_path)
    if broll_reader is None and base_p.exists() and visual.provider_used not in ("pil_35mm_cinema_plate", "pil_document_renderer", "pil_kinetic_renderer"):
        try:
            bg_source = Image.open(base_p).convert("RGB").resize((1480, 832))
        except Exception:
            bg_source = None

    cmd = [
        ffmpeg, "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-an", str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert proc.stdin is not None

    ps = scene.get("parallax_spec") or {}
    mid_label = str(ps.get("midground_main") or scene.get("flux_base_image_prompt", ""))[:68].upper()
    doc_data = scene.get("document_asset") or {}
    hl_str = str(doc_data.get("highlight_text") or scene.get("voiceover_text", ""))
    ev_refs = ", ".join(scene.get("evidence_refs") or [f"EV_{idx_num:03d}"])

    try:
        for f_idx in range(total_frames):
            t = f_idx / float(fps)
            prog = t / max(0.1, duration_sec)

            # Kiểm tra xem có đang ở thời điểm nổ SFX (trigger_word) không -> Tạo hiệu ứng rung Camera + Chớp sáng!
            shake_x, shake_y, flash_alpha = 0, 0, 0
            for tt in trig_times:
                dt = t - tt
                if 0.0 <= dt <= 0.38:
                    decay = math.exp(-7.0 * dt)
                    shake_x = int(math.sin(dt * 95.0) * 14 * decay)
                    shake_y = int(math.cos(dt * 110.0) * 10 * decay)
                    flash_alpha = int(85 * decay)

            # 1. NỀN ĐỘNG (Video B-roll thật từ yt-dlp/Pixabay HOẶC ảnh 35mm HOẶC đèn cấp cứu)
            raw_broll = broll_reader.stdout.read(w * h * 3) if (broll_reader and broll_reader.stdout) else b""
            if len(raw_broll) == w * h * 3:
                img = Image.frombytes("RGB", (w, h), raw_broll)
                draw = ImageDraw.Draw(img, "RGBA")
                draw.rectangle((0, 0, w, h), fill=(4, 8, 14, 105))
            elif bg_source is not None:
                pan_x = int(90 * prog) + shake_x
                pan_y = int(50 * prog) + shake_y
                pan_x = max(0, min(bg_source.width - w, pan_x))
                pan_y = max(0, min(bg_source.height - h, pan_y))
                img = bg_source.crop((pan_x, pan_y, pan_x + w, pan_y + h)).copy()
                draw = ImageDraw.Draw(img, "RGBA")
                draw.rectangle((0, 0, w, h), fill=(5, 9, 15, 115))
            else:
                pulse_r = int(12 + 10 * max(0.0, math.sin(t * 4.5)))
                pulse_b = int(26 + 14 * max(0.0, math.cos(t * 3.8)))
                img = Image.new("RGB", (w, h), (pulse_r, 14, pulse_b))
                draw = ImageDraw.Draw(img, "RGBA")

            # Lưới tọa độ dịch chuyển liên tục (Moving Parallax Grid)
            grid_offset_x = int((t * 38) % 64) + shake_x
            grid_offset_y = int((t * 22) % 64) + shake_y
            for gx in range(grid_offset_x - 64, w, 64):
                draw.line((gx, 55, gx, h - 55), fill=(56, 189, 248, 16), width=1)
            for gy in range(grid_offset_y + 55, h - 55, 64):
                draw.line((0, gy, w, gy), fill=(56, 189, 248, 16), width=1)

            # 2. VẼ ĐỒ HỌA CHUYỂN ĐỘNG THEO TỪNG ARCHETYPE
            if archetype == "LIVE_BIOMETRIC_MONITOR":
                # Khung máy theo dõi sinh tồn ICU chạy sóng thời gian thực
                draw.rounded_rectangle((85 + shake_x, 82 + shake_y, 1195 + shake_x, 545 + shake_y), radius=12, fill=(4, 10, 16, 225), outline=(56, 189, 248, 110), width=2)
                is_flatlined = t >= (trig_times[0] if trig_times else duration_sec * 0.42)
                bpm_val = 0 if is_flatlined else int(134 + 12 * math.sin(t * 6.0))
                spo2_val = "--" if is_flatlined else f"{int(91 - 8 * prog)}%"
                status_col = (239, 68, 68) if is_flatlined else (16, 185, 129)

                draw.text((115 + shake_x, 102 + shake_y), "ICU TELEMETRY // CONTINUOUS ECG & cEEG WAVEFORM", fill=(148, 163, 184), font=f_hud)
                draw.text((920 + shake_x, 100 + shake_y), f"HR: {bpm_val:03d} BPM", fill=status_col, font=f_title)
                draw.text((920 + shake_x, 138 + shake_y), f"SpO2: {spo2_val} // {ev_refs}", fill=(251, 191, 36), font=f_hud)

                # Vẽ đường sóng ECG chạy từ trái sang phải theo thời gian thực t
                head_x = 120 + int(((t * 360) % 1020))
                ecg_pts = []
                for x in range(120, head_x, 5):
                    if is_flatlined and x > 420:
                        y = 265 + int(rng.uniform(-1.5, 1.5))
                    else:
                        phase_w = ((x - t * 240) % 140) / 140.0
                        if 0.42 <= phase_w <= 0.46:
                            y = 165
                        elif 0.46 < phase_w <= 0.50:
                            y = 335
                        elif 0.50 < phase_w <= 0.55:
                            y = 220
                        else:
                            y = 265 + int(8 * math.sin(phase_w * math.pi * 2))
                    ecg_pts.append((x + shake_x, y + shake_y))
                if len(ecg_pts) > 2:
                    draw.line(ecg_pts, fill=status_col, width=4)
                    lx, ly = ecg_pts[-1]
                    draw.ellipse((lx - 6, ly - 6, lx + 6, ly + 6), fill=(255, 255, 255, 255))

                # Đường sóng thứ 2: Sóng não Gamma bùng nổ sau khi tim ngừng đập!
                eeg_pts = []
                for x in range(120, 1140, 6):
                    burst = 38.0 if is_flatlined else 9.0
                    y_eeg = 425 + int(burst * math.sin(x * 0.14 - t * 22.0) * math.cos(x * 0.05 + t * 9.0))
                    eeg_pts.append((x + shake_x, y_eeg + shake_y))
                draw.line(eeg_pts, fill=(251, 191, 36, 215), width=2)
                draw.text((120 + shake_x, 495 + shake_y), f"VISUAL FOCUS: {mid_label}", fill=(226, 232, 240), font=f_doc_sm)

            elif archetype == "LIVE_DOCUMENT":
                # Hiệu ứng tờ tài liệu trượt vào + bút dạ quang vàng quét ngang từng frame + đóng dấu đỏ
                slide_y = int(max(0.0, (0.35 - t) * 180))
                doc_l, doc_t, doc_r, doc_b = 140 + shake_x, 78 + slide_y + shake_y, 1140 + shake_x, 555 + slide_y + shake_y
                draw.rounded_rectangle((doc_l, doc_t, doc_r, doc_b), radius=8, fill=(244, 241, 232, 252), outline=(148, 163, 184, 255), width=2)
                draw.rectangle((doc_l, doc_t, doc_r, doc_t + 52), fill=(15, 23, 42, 255))
                draw.text((doc_l + 24, doc_t + 16), f"FORENSIC EVIDENCE RECORD // {ev_refs}", fill=(248, 250, 252), font=f_hud)

                for ry, rw in [(doc_t + 78, 520), (doc_t + 104, 780), (doc_t + 130, 410)]:
                    draw.rectangle((doc_l + 30, ry, doc_l + 30 + rw, ry + 14), fill=(203, 213, 225, 255))

                # Quét bút dạ quang màu vàng từ trái sang phải theo thời gian thực (t từ 0.4s -> 2.8s)
                sweep_ratio = max(0.0, min(1.0, (t - 0.35) / 2.2))
                hl_max_w = 920
                cur_hl_w = int(hl_max_w * sweep_ratio)
                if cur_hl_w > 4:
                    draw.rounded_rectangle((doc_l + 26, doc_t + 175, doc_l + 26 + cur_hl_w, doc_t + 295), radius=6, fill=(253, 224, 71, 225))

                lines_doc = textwrap.wrap(hl_str, width=54)[:3]
                for i, ln in enumerate(lines_doc):
                    draw.text((doc_l + 42, doc_t + 188 + i * 32), ln, fill=(15, 23, 42), font=f_doc)

                draw.text((doc_l + 32, doc_t + 335), f"SCENE TARGET: {mid_label}", fill=(51, 65, 85), font=f_doc_sm)

                # Đóng dấu đỏ [CRITICAL DISCREPANCY] khi chạm mốc nổ SFX
                if t >= (trig_times[0] if trig_times else duration_sec * 0.45):
                    draw.rounded_rectangle((doc_r - 365, doc_t + 320, doc_r - 35, doc_t + 390), radius=6, fill=(220, 38, 38, 35), outline=(220, 38, 38, 245), width=4)
                    draw.text((doc_r - 345, doc_t + 342), "TIMESTAMP DISCREPANCY", fill=(220, 38, 38), font=f_doc)

            elif archetype == "LIVE_DATA_NETWORK":
                # Sơ đồ mạng lưới điều tra + bộ đếm số nhảy liên tục từng frame
                nodes = [(240, 210, "HOSPITAL ICU"), (640, 165, "DEATH RECORD"), (1030, 215, "OPO PROCUREMENT"), (420, 435, "INSURANCE LEDGER"), (860, 435, "TRANSPLANT QUOTA")]
                edges = [(0, 1), (1, 2), (0, 3), (1, 4), (3, 4), (2, 4)]

                # Tia kết nối tự vẽ dần theo tiến độ prog
                active_edges = int(min(len(edges), prog * (len(edges) + 1.5)))
                for e_i in range(active_edges):
                    n1, n2 = nodes[edges[e_i][0]], nodes[edges[e_i][1]]
                    draw.line((n1[0] + shake_x, n1[1] + shake_y, n2[0] + shake_x, n2[1] + shake_y), fill=(239, 68, 68, 195), width=3)

                for nx, ny, nlabel in nodes:
                    r_pulse = 28 + int(5 * math.sin(t * 6.0 + nx))
                    draw.ellipse((nx - r_pulse + shake_x, ny - r_pulse + shake_y, nx + r_pulse + shake_x, ny + r_pulse + shake_y), fill=(15, 23, 42, 240), outline=(251, 191, 36, 220), width=3)
                    draw.text((nx - 70 + shake_x, ny + 36 + shake_y), nlabel, fill=(226, 232, 240), font=f_hud)

                counter_val = int(min(1.0, prog * 1.25) * 4850000000)
                draw.rounded_rectangle((330 + shake_x, 265 + shake_y, 950 + shake_x, 385 + shake_y), radius=10, fill=(6, 10, 18, 238), outline=(251, 191, 36, 180), width=2)
                draw.text((365 + shake_x, 282 + shake_y), f"INDUSTRY VALUATION // {ev_refs}", fill=(148, 163, 184), font=f_hud)
                draw.text((365 + shake_x, 312 + shake_y), f"${counter_val:,}", fill=(251, 191, 36), font=f_big_num)

            else:
                # LIVE_CORRIDOR_SCAN: Khung ống ngắm camera điều tra 3D dịch chuyển + sóng âm thanh (Audio Spectrum Bars)
                cx = int(640 + 110 * math.sin(t * 1.3)) + shake_x
                cy = int(310 + 45 * math.cos(t * 1.7)) + shake_y
                for ring_r in (190, 135, 80):
                    draw.ellipse((cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r), outline=(56, 189, 248, 95), width=2)
                draw.line((cx - 220, cy, cx + 220, cy), fill=(239, 68, 68, 140), width=1)
                draw.line((cx, cy - 220, cx, cy + 220), fill=(239, 68, 68, 140), width=1)

                # Sóng phổ âm thanh (Live Audio Spectrum Visualizer) nhảy theo giọng nói
                for b_i in range(36):
                    bx = 210 + b_i * 24 + shake_x
                    bh = int(18 + 65 * abs(math.sin(t * 11.0 + b_i * 0.45)) * (0.4 + 0.6 * math.cos(b_i * 0.2)))
                    draw.rectangle((bx, 510 - bh + shake_y, bx + 14, 510 + shake_y), fill=(56, 189, 248, 190))

                draw.rounded_rectangle((140 + shake_x, 105 + shake_y, 1140 + shake_x, 195 + shake_y), radius=8, fill=(6, 11, 19, 215), outline=(56, 189, 248, 90), width=1)
                draw.text((165 + shake_x, 122 + shake_y), f"FORENSIC RECONSTRUCTION // {sid}", fill=(56, 189, 248), font=f_hud)
                draw.text((165 + shake_x, 148 + shake_y), mid_label, fill=(248, 250, 252), font=f_doc)

            # 3. HẠT BỤI 3D, THANH TIMECODE CHẠY TỪNG MILI-GIÂY & CHỚP SÁNG KHI NỔ SFX
            _draw_particles_and_scanlines(draw, w, h, t, particles, (56, 189, 248))

            if flash_alpha > 0:
                draw.rectangle((0, 0, w, h), fill=(255, 245, 220, flash_alpha))

            # Thanh Cinema Top Bar với đồng hồ Timecode chạy thực tế từng frame (00:00:03:18)
            draw.rectangle((0, 0, w, 52), fill=(0, 0, 0, 225))
            tc_sec = int(t)
            tc_frm = f_idx % fps
            draw.text((36, 16), f"● REC  {sid} // {archetype} // TC 00:00:{tc_sec:02d}:{tc_frm:02d}", fill=(239, 68, 68), font=f_hud)
            draw.text((920, 16), f"EVIDENCE: {ev_refs}", fill=(148, 163, 184), font=f_hud)

            # 4. PHỤ ĐỀ ĐỘNG TỪNG TỪ (Word-by-Word Pop-in Karaoke)
            _draw_word_by_word_subtitle(
                draw, w, h, t, voice_out, scene.get("voiceover_text", ""), trig_words, f_sub, f_sub_big
            )

            proc.stdin.write(img.tobytes())

        proc.stdin.close()
        proc.wait(timeout=45)
        if broll_reader:
            try:
                broll_reader.kill()
            except Exception:
                pass
        return out_mp4.exists() and out_mp4.stat().st_size > 1000
    except Exception:
        if broll_reader:
            try:
                broll_reader.kill()
            except Exception:
                pass
        try:
            proc.kill()
        except Exception:
            pass
        return False


def render_scene_motion(
    scene: dict,
    visual: VisualSceneOutput,
    duration_sec: float,
    out_dir: Path,
    force_local: bool = False,
    voice_out: Optional[VoiceSceneOutput] = None,
) -> MotionSceneOutput:
    """Render clip chuyển động 30fps sống động cho 1 cảnh (TALKING_HEAD Lip-Sync / Muse Video API / B-Roll / 30fps Live Motion Graphics)."""
    from agent_04_motion_broll.muse_video_adapter import (
        generate_broll_via_muse,
        generate_talking_head_clip,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    sid = scene["scene_id"]
    cam = scene.get("camera_move") or "SLOW_PUSH_IN"
    mode = scene.get("visual_mode", "STATIC_PARALLAX")
    out_mp4 = out_dir / f"{sid}.mp4"
    dur = max(1.5, round(duration_sec, 2))

    engine_type = "local_25d_parallax"
    if mode == "TALKING_HEAD":
        engine_type = generate_talking_head_clip(
            scene=scene,
            visual=visual,
            voice_out=voice_out,
            duration_sec=dur,
            out_mp4=out_mp4,
            force_local=force_local,
        )
    else:
        muse_engine = None
        if mode == "AI_VIDEO" and not force_local:
            muse_engine = generate_broll_via_muse(
                image_path=Path(visual.base_image_path),
                motion_prompt=str(scene.get("video_motion_prompt") or scene.get("flux_base_image_prompt") or ""),
                duration_sec=dur,
                out_mp4=out_mp4,
            )

        if muse_engine:
            engine_type = muse_engine
        else:
            ok = _render_live_30fps_scene(scene, visual, voice_out, dur, out_mp4, fps=30, force_local=force_local)
            if not ok:
                out_mp4.write_bytes(b"")
            if mode == "DOCUMENT_HIGHLIGHT":
                engine_type = "document_anim"
            elif mode == "KINETIC_DATA_CARD":
                engine_type = "kinetic_card_anim"

    return MotionSceneOutput(
        scene_id=sid,
        video_clip_path=str(out_mp4),
        duration_sec=dur,
        motion_engine=engine_type,
        camera_move=cam,
    )
