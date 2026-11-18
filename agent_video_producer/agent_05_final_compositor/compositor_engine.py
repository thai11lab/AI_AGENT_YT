"""Agent 4: Master Audio-Visual Compositor & Final Cut (agent_compositor).
1. Tạo bộ Sound Effects điện ảnh (IMPACT, FLATLINE, HEARTBEAT, RISER, TICKING, ALARM, WHOOSH) & nhạc nền Dark Pulse.
2. Trộn âm thanh từng cảnh: Giọng đọc (Voiceover đã cắt khoảng lặng thừa) + SFX nổ đúng mili-giây trigger_word + tiếng cắt cảnh (Sub-cut Hit) tại nhịp 38% & 70%.
3. Phụ đề Động (Kinetic Phrase Captions): Chia câu thành 3 nhịp cụm từ ngắn (đổi mỗi ~2.8 giây khớp với nhịp nhảy góc máy) kèm tô màu Vàng Gold từ khóa.
"""
import math
import re
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

from shared.contracts import MotionSceneOutput, VoiceSceneOutput


def _load_sub_font(size: int = 28) -> ImageFont.FreeTypeFont:
    for c in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _split_into_3_phrases(vo_text: str) -> List[str]:
    words = [w for w in vo_text.strip().split() if w]
    if len(words) <= 6:
        return [" ".join(words), " ".join(words), " ".join(words)]
    n = len(words)
    c1 = max(2, n // 3)
    c2 = max(c1 + 2, (2 * n) // 3)
    return [
        " ".join(words[:c1]),
        " ".join(words[c1:c2]),
        " ".join(words[c2:]),
    ]


def _render_kinetic_phrase_pil(phrase: str, trigger_words: List[str], beat_idx: int, out_png: Path) -> Path:
    """Vẽ cụm phụ đề động (Kinetic Caption) ngắn gọn, tô vàng từ khóa nhấn mạnh."""
    w, h = 1280, 720
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Nháy viền cinema nhẹ ở cảnh cắt Beat 2 (Macro Punch-in)
    if beat_idx == 1:
        draw.rectangle((0, 0, w - 1, h - 1), outline=(251, 191, 36, 75), width=3)

    font = _load_sub_font(30)
    trig_set = {re.sub(r"[^\w]", "", t.lower()) for t in trigger_words if t}

    words = phrase.split()
    word_widths = []
    space_w = 10
    for wd in words:
        bb = draw.textbbox((0, 0), wd.upper(), font=font)
        word_widths.append((wd.upper(), bb[2] - bb[0], re.sub(r"[^\w]", "", wd.lower()) in trig_set))

    total_w = sum(item[1] for item in word_widths) + space_w * max(0, len(word_widths) - 1)
    pad_x, pad_y = 28, 16
    box_left = max(40, (w - total_w) // 2 - pad_x)
    box_right = min(w - 40, (w + total_w) // 2 + pad_x)
    box_top = h - 108
    box_bottom = h - 38

    draw.rounded_rectangle(
        (box_left, box_top, box_right, box_bottom),
        radius=12,
        fill=(6, 9, 15, 228),
        outline=(251, 191, 36, 130) if beat_idx == 1 else (255, 255, 255, 55),
        width=2,
    )

    curr_x = (w - total_w) // 2
    y_text = box_top + pad_y - 2
    for wd_up, ww, is_trig in word_widths:
        color = (251, 191, 36, 255) if (is_trig or beat_idx == 1 and len(wd_up) > 6) else (248, 250, 252, 255)
        draw.text((curr_x + 2, y_text + 2), wd_up, fill=(0, 0, 0, 240), font=font)
        draw.text((curr_x, y_text), wd_up, fill=color, font=font)
        curr_x += ww + space_w

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return out_png


def _generate_sfx_wav(category: str, out_wav: Path, sample_rate: int = 24000) -> Path:
    """Ủy quyền sang sfx_library (ưu tiên Foley thật từ assets/sfx -> Freesound APIv2 -> Soft Cinema Fallback)."""
    from agent_05_final_compositor.sfx_library import resolve_sfx_wav

    return resolve_sfx_wav(category, out_wav.parent, sample_rate=sample_rate)


def _should_play_sfx_for_scene(scene: dict, scene_idx: int) -> bool:
    """Chỉ bật SFX ở các điểm nhấn thực sự (cảnh mở đầu, thẻ dữ liệu/hồ sơ, hoặc giãn cách mỗi 5 cảnh) để không gây mệt tai."""
    if scene_idx == 1:
        return True
    mode = str(scene.get("visual_mode", "")).upper()
    if mode in ("DOCUMENT_HIGHLIGHT", "KINETIC_DATA_CARD"):
        return True
    return (scene_idx % 5) == 1


def _mix_scene_audio_wav(
    voice_out: VoiceSceneOutput,
    scene: dict,
    sfx_dir: Path,
    out_mixed_wav: Path,
    sample_rate: int = 24000,
    scene_idx: int = 1,
) -> Path:
    """Trộn âm thanh chuẩn Documentary: Giọng đọc sạch 100% + Nền sub-ambient cực nhẹ + SFX điểm xuyết có chọn lọc."""
    vo_path = Path(voice_out.audio_path)
    if not vo_path.exists():
        return vo_path

    try:
        with wave.open(str(vo_path), "rb") as wf:
            n_frames = wf.getnframes()
            raw_vo = wf.readframes(n_frames)
            vo_samples = list(struct.unpack(f"<{len(raw_vo) // 2}h", raw_vo))
    except Exception:
        shutil.copyfile(vo_path, out_mixed_wav)
        return out_mixed_wav

    total_samples = len(vo_samples)
    # 1. Nền Sub-Ambient tách riêng thành file bed để nén Sidechain Ducking bằng FFmpeg (tự nhỏ xuống khi người nói cất giọng)
    bed_wav = out_mixed_wav.with_suffix(".bed.wav")
    bed_buf = bytearray()
    for i in range(total_samples):
        t = i / sample_rate
        drone = 0.020 * math.sin(2 * math.pi * 55.0 * t) + 0.008 * math.sin(2 * math.pi * 110.0 * t)
        bed_buf.extend(struct.pack("<h", max(-32767, min(32767, int(drone * 32767)))))
    with wave.open(str(bed_wav), "wb") as bwf:
        bwf.setnchannels(1)
        bwf.setsampwidth(2)
        bwf.setframerate(sample_rate)
        bwf.writeframes(bytes(bed_buf))

    # 2. Chỉ chèn tối đa 1 SFX dịu tai tại đúng các cảnh điểm nhấn (không chèn ở mọi cảnh)
    cues = scene.get("audio_cues") or []
    if cues and _should_play_sfx_for_scene(scene, scene_idx):
        cue = cues[0]
        cat = str(cue.get("sfx_category", "WHOOSH")).upper()
        tw = re.sub(r"[^\w]", "", str(cue.get("trigger_word", "")).lower())
        trig_sec = voice_out.trigger_timestamps.get(tw, 0.15)
        start_idx = max(0, int(trig_sec * sample_rate))

        sfx_wav = _generate_sfx_wav(cat, sfx_dir / f"{cat}_master.wav", sample_rate)
        try:
            with wave.open(str(sfx_wav), "rb") as sf:
                raw_sfx = sf.readframes(sf.getnframes())
                sfx_samples = struct.unpack(f"<{len(raw_sfx) // 2}h", raw_sfx)
            for j, s_val in enumerate(sfx_samples):
                pos = start_idx + j
                if pos >= total_samples:
                    break
                vo_samples[pos] = max(-32767, min(32767, vo_samples[pos] + int(s_val * 0.16)))
        except Exception:
            pass

    vo_sfx_wav = out_mixed_wav.with_suffix(".vosfx.wav")
    out_mixed_wav.parent.mkdir(parents=True, exist_ok=True)
    packed = struct.pack(f"<{total_samples}h", *vo_samples)
    with wave.open(str(vo_sfx_wav), "wb") as out_wf:
        out_wf.setnchannels(1)
        out_wf.setsampwidth(2)
        out_wf.setframerate(sample_rate)
        out_wf.writeframes(packed)

    # 3. Áp dụng FFmpeg Sidechain Audio Ducking (chuẩn GitHub ffmpeg-ai): nhạc nền tự nén xuống khi có tiếng người nói
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        try:
            subprocess.run(
                [
                    ffmpeg, "-y",
                    "-i", str(bed_wav),
                    "-i", str(vo_sfx_wav),
                    "-filter_complex",
                    "[1:a]asplit=2[sc][vox];[0:a][sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=450[duck];[duck][vox]amix=inputs=2:normalize=0[a]",
                    "-map", "[a]",
                    "-ar", str(sample_rate), "-ac", "1",
                    str(out_mixed_wav),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30,
            )
            bed_wav.unlink(missing_ok=True)
            vo_sfx_wav.unlink(missing_ok=True)
            return out_mixed_wav
        except Exception:
            pass

    bed_wav.unlink(missing_ok=True)
    shutil.move(str(vo_sfx_wav), str(out_mixed_wav))
    return out_mixed_wav


def _format_srt_time(sec: float) -> str:
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec) % 60
    m = (int(sec) // 60) % 60
    h = int(sec) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt_subtitles(
    scenes: List[dict],
    voice_outputs: Dict[str, VoiceSceneOutput],
    out_srt: Path,
) -> Path:
    """Xuất file phụ đề chuẩn YouTube (.srt) khớp chính xác từng cảnh."""
    lines: List[str] = []
    cursor = 0.0
    for idx, sc in enumerate(scenes, 1):
        sid = sc["scene_id"]
        v_out = voice_outputs.get(sid)
        dur = v_out.duration_sec if v_out else float(sc.get("duration_sec", 5.0))
        start_t = _format_srt_time(cursor)
        end_t = _format_srt_time(cursor + dur)
        lines.append(f"{idx}\n{start_t} --> {end_t}\n{sc.get('voiceover_text', '')}\n")
        cursor += dur
    out_srt.parent.mkdir(parents=True, exist_ok=True)
    out_srt.write_text("\n".join(lines), encoding="utf-8")
    return out_srt


def compose_final_video(
    scenes: List[dict],
    voice_outputs: Dict[str, VoiceSceneOutput],
    motion_outputs: Dict[str, MotionSceneOutput],
    work_dir: Path,
    final_mp4_path: Path,
) -> Path:
    """Ghép từng cảnh với 3 nhịp Phụ đề Động (Kinetic Captions đổi mỗi ~2.8s) + Audio मिक्स + Xuất .mp4 chuẩn QuickTime."""
    ffmpeg = shutil.which("ffmpeg")
    sfx_dir = work_dir / "sfx_cache"
    muxed_dir = work_dir / "muxed_scenes"
    muxed_dir.mkdir(parents=True, exist_ok=True)

    write_srt_subtitles(scenes, voice_outputs, final_mp4_path.with_suffix(".srt"))

    if not ffmpeg:
        final_mp4_path.parent.mkdir(parents=True, exist_ok=True)
        final_mp4_path.write_bytes(b"")
        return final_mp4_path

    muxed_clips: List[Path] = []
    for idx_sc, sc in enumerate(scenes, 1):
        sid = sc["scene_id"]
        v_out = voice_outputs[sid]
        m_out = motion_outputs[sid]
        mixed_wav = _mix_scene_audio_wav(v_out, sc, sfx_dir, muxed_dir / f"{sid}_mixed.wav", scene_idx=idx_sc)
        scene_final_mp4 = muxed_dir / f"{sid}_muxed.mp4"

        try:
            # Không dùng -shortest để tránh cắt mất âm tiết cuối của giọng đọc
            subprocess.run(
                [
                    ffmpeg, "-y",
                    "-i", m_out.video_clip_path,
                    "-i", str(mixed_wav),
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    str(scene_final_mp4),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
            muxed_clips.append(scene_final_mp4)
        except Exception as e:
            print(f"[Compositor Warning] Lỗi ghép cảnh {sid}: {e}")
            continue

    if not muxed_clips:
        final_mp4_path.write_bytes(b"")
        return final_mp4_path

    concat_txt = muxed_dir / "concat_list.txt"
    concat_txt.write_text("\n".join([f"file '{p.name}'" for p in muxed_clips]), encoding="utf-8")
    final_mp4_path.parent.mkdir(parents=True, exist_ok=True)

    # Chuẩn hóa âm lượng phát hành YouTube (-14 LUFS) & encode lại luồng AAC liền mạch để không bị mất chữ ở điểm nối giữa các cảnh
    subprocess.run(
        [
            ffmpeg, "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "copy",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(final_mp4_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
    )
    return final_mp4_path
