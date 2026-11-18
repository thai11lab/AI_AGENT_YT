"""Universal Muse Video-Gen & Audio-Driven Talking-Head Lip-Sync Adapter (Agent 04).
Phủ mọi trường hợp dựng video có nhân vật nói chuyện (TALKING_HEAD) & cảnh hành động (AI_VIDEO / GTA B-Roll):
1. Muse Cloud API (`MUSE_API_KEY` / `MUSE_API_URL` trong .env):
   - `generate_talking_head_clip`: Gửi ảnh nhân vật + file .wav (từ OmniVoice/Kokoro) để Muse sinh video khớp khẩu hình 100%.
   - `generate_broll_via_muse`: Gửi ảnh gốc + motion prompt để Muse sinh video hành động đúng thời lượng câu thoại.
2. Local Mac M4 Fallback ($0):
   - Tự động kiểm tra Local MuseTalk Server (`http://127.0.0.1:8895/lipsync`) nếu có.
   - Nếu chưa bật server GPU, tự động chạy **Audio-Reactive Talking-Head 30fps Animator**: đọc trực tiếp biên độ sóng âm từng mili-giây từ file `.wav` để tạo nhịp thở, chuyển động đầu/vai, vòng sáng phát âm và sóng âm thanh khớp 100% với tiếng nói.
"""
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import List, Optional

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from shared.contracts import VisualSceneOutput, VoiceSceneOutput
from shared.env import get_env_key


def extract_wav_rms_envelope(wav_path: Path, fps: int = 30) -> List[float]:
    """Đọc file .wav thật và trích xuất đường bao năng lượng (RMS) chuẩn hóa [0.0..1.0] cho từng frame 30fps."""
    if not wav_path.exists():
        return []
    try:
        with wave.open(str(wav_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            rate = wf.getframerate()
            n_frames = wf.getnframes()
            if sampwidth != 2 or rate <= 0 or n_frames <= 0:
                return []
            raw = wf.readframes(n_frames)

        total_samples = len(raw) // 2
        samples = struct.unpack(f"<{total_samples}h", raw)
        if n_channels > 1:
            samples = samples[::n_channels]

        step = max(1, int(rate / fps))
        rms_vals: List[float] = []
        for i in range(0, len(samples), step):
            chunk = samples[i : i + step]
            if not chunk:
                break
            sq = sum(s * s for s in chunk) / float(len(chunk))
            rms_vals.append(math.sqrt(sq))

        if not rms_vals:
            return []
        peak = max(rms_vals) or 1.0
        return [min(1.0, round(v / peak, 3)) for v in rms_vals]
    except Exception:
        return []


def _fit_clip_duration_ffmpeg(src_mp4: Path, dst_mp4: Path, target_dur: float) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not src_mp4.exists() or src_mp4.stat().st_size < 1000:
        return False
    try:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-stream_loop",
                "-1",
                "-i",
                str(src_mp4),
                "-t",
                f"{target_dur:.2f}",
                "-vf",
                "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=30",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-pix_fmt",
                "yuv420p",
                str(dst_mp4),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
        )
        return dst_mp4.exists() and dst_mp4.stat().st_size > 1000
    except Exception:
        return False


def generate_broll_via_muse(
    image_path: Path,
    motion_prompt: str,
    duration_sec: float,
    out_mp4: Path,
) -> Optional[str]:
    """Gọi Muse Video-Gen API (nếu có MUSE_API_KEY) để gen video hành động từ ảnh gốc + motion prompt."""
    muse_key = get_env_key("MUSE_API_KEY")
    muse_url = get_env_key("MUSE_VIDEO_API_URL", "https://api.muse.ai/v1/video/generate")
    if not muse_key:
        return None

    tmp_raw = out_mp4.with_suffix(".muse_raw.mp4")
    try:
        headers = {"Authorization": f"Bearer {muse_key}"}
        with httpx.Client(timeout=90.0, follow_redirects=True) as client:
            if image_path.exists():
                with open(image_path, "rb") as img_f:
                    resp = client.post(
                        muse_url,
                        headers=headers,
                        data={"prompt": motion_prompt, "duration": str(min(10.0, max(3.0, duration_sec)))},
                        files={"image": (image_path.name, img_f, "image/png")},
                    )
            else:
                resp = client.post(
                    muse_url,
                    headers=headers,
                    json={"prompt": motion_prompt, "duration": min(10.0, max(3.0, duration_sec))},
                )
            if resp.status_code >= 400:
                return None

            ctype = resp.headers.get("content-type", "")
            if "video" in ctype or len(resp.content) > 50000:
                tmp_raw.write_bytes(resp.content)
            else:
                data = resp.json()
                vid_url = data.get("video_url") or (data.get("video") or {}).get("url")
                if not vid_url:
                    return None
                tmp_raw.write_bytes(client.get(vid_url).content)

        if _fit_clip_duration_ffmpeg(tmp_raw, out_mp4, duration_sec):
            tmp_raw.unlink(missing_ok=True)
            return "muse_video_api"
    except Exception:
        pass
    tmp_raw.unlink(missing_ok=True)
    return None


def _try_muse_or_cloud_lipsync(
    image_path: Path,
    audio_wav: Path,
    duration_sec: float,
    out_mp4: Path,
) -> Optional[str]:
    """Thử lần lượt: 1. Muse Lip-Sync API -> 2. Local MuseTalk Server -> None."""
    muse_key = get_env_key("MUSE_API_KEY")
    muse_ls_url = get_env_key("MUSE_LIPSYNC_API_URL", "https://api.muse.ai/v1/lipsync/generate")
    local_musetalk_url = get_env_key("MUSETALK_LOCAL_URL", "http://127.0.0.1:8895/lipsync")

    endpoints = []
    if muse_key:
        endpoints.append(("muse_lipsync_api", muse_ls_url, {"Authorization": f"Bearer {muse_key}"}, 90.0))
    endpoints.append(("local_musetalk", local_musetalk_url, {}, 5.0))

    if not image_path.exists() or not audio_wav.exists():
        return None

    tmp_raw = out_mp4.with_suffix(".ls_raw.mp4")
    for eng_name, url, hdrs, t_out in endpoints:
        try:
            with httpx.Client(timeout=t_out, follow_redirects=True) as client:
                with open(image_path, "rb") as f_img, open(audio_wav, "rb") as f_aud:
                    resp = client.post(
                        url,
                        headers=hdrs,
                        files={
                            "image": (image_path.name, f_img, "image/png"),
                            "audio": (audio_wav.name, f_aud, "audio/wav"),
                        },
                    )
                if resp.status_code >= 400:
                    continue
                ctype = resp.headers.get("content-type", "")
                if "video" in ctype or len(resp.content) > 50000:
                    tmp_raw.write_bytes(resp.content)
                else:
                    vid_url = resp.json().get("video_url") or (resp.json().get("video") or {}).get("url")
                    if not vid_url:
                        continue
                    tmp_raw.write_bytes(client.get(vid_url).content)

                if _fit_clip_duration_ffmpeg(tmp_raw, out_mp4, duration_sec):
                    tmp_raw.unlink(missing_ok=True)
                    return eng_name
        except Exception:
            continue
    tmp_raw.unlink(missing_ok=True)
    return None


def _render_audio_reactive_talking_head(
    scene: dict,
    visual: VisualSceneOutput,
    voice_out: Optional[VoiceSceneOutput],
    duration_sec: float,
    out_mp4: Path,
    fps: int = 30,
) -> bool:
    """Fallback M4 0đ: Dựng Talking-Head 30fps phản ứng theo đúng biên độ sóng âm (.wav) từng frame (nhịp thở, nhún nhẹ, vòng sáng phát âm, phụ đề Karaoke)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False

    w, h = 1280, 720
    # Làm tròn lên (+2 frames) để video luôn dài >= audio, tuyệt đối không bị cắt cụt từ cuối câu
    total_frames = max(15, math.ceil(duration_sec * fps) + 2)
    wav_path = Path(voice_out.audio_path) if voice_out and voice_out.audio_path else Path("")
    rms_env = extract_wav_rms_envelope(wav_path, fps=fps)

    # Nạp ảnh nhân vật/cảnh gốc làm nền & chân dung khung tròn/vuông điện ảnh
    src_img_path = Path(visual.base_image_path)
    if src_img_path.exists():
        base_img = Image.open(src_img_path).convert("RGB").resize((w, h), Image.Resampling.LANCZOS)
    else:
        base_img = Image.new("RGB", (w, h), (15, 23, 42))

    bg_blurred = base_img.filter(ImageFilter.GaussianBlur(radius=14)).point(lambda p: int(p * 0.42))
    portrait_base = base_img.resize((440, 440), Image.Resampling.LANCZOS)

    try:
        f_hud = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 18)
        f_sub = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 34)
    except Exception:
        f_hud = ImageFont.load_default()
        f_sub = ImageFont.load_default()

    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-s",
        f"{w}x{h}",
        "-pix_fmt",
        "rgb24",
        "-r",
        str(fps),
        "-i",
        "-",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        str(out_mp4),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if proc.stdin is None:
        return False

    vo_words = str(scene.get("voiceover_text", "")).split()
    sid = scene.get("scene_id", "S001")

    try:
        for f_idx in range(total_frames):
            t = f_idx / float(fps)
            amp = rms_env[f_idx] if f_idx < len(rms_env) else (0.35 + 0.35 * abs(math.sin(t * 7.5)))
            frame = bg_blurred.copy().convert("RGBA")
            draw = ImageDraw.Draw(frame, "RGBA")

            # Nhân vật nhún nhẹ theo nhịp thở và đẩy scale nhẹ khi nói to
            bob_y = int(math.sin(t * 2.8) * 3 - amp * 6)
            scale_px = int(amp * 14)
            pw = 440 + scale_px
            p_resized = portrait_base.resize((pw, pw), Image.Resampling.BILINEAR)

            px = (w - pw) // 2
            py = 85 + bob_y - scale_px // 2

            # Vòng sáng Audio-Reactive xung quanh nhân vật khớp biên độ tiếng nói
            glow_alpha = int(70 + amp * 170)
            draw.rounded_rectangle(
                (px - 8, py - 8, px + pw + 8, py + pw + 8),
                radius=24,
                outline=(56, 189, 248, glow_alpha),
                width=4,
            )
            frame.paste(p_resized.convert("RGBA"), (px, py))

            # Thanh sóng âm thanh 2 bên đối xứng nhảy theo RMS thật
            mid_y = py + pw // 2
            for b in range(14):
                bar_h = int(12 + amp * 115 * (0.45 + 0.55 * abs(math.sin(t * 14.0 + b * 0.6))))
                lx = px - 36 - b * 18
                rx = px + pw + 24 + b * 18
                draw.rectangle((lx, mid_y - bar_h // 2, lx + 10, mid_y + bar_h // 2), fill=(56, 189, 248, 190))
                draw.rectangle((rx, mid_y - bar_h // 2, rx + 10, mid_y + bar_h // 2), fill=(56, 189, 248, 190))

            # Header HUD
            draw.rectangle((0, 0, w, 46), fill=(0, 0, 0, 210))
            draw.text((28, 13), f"● TALKING HEAD // {sid} // VOICE-SYNC ACTIVE", fill=(56, 189, 248), font=f_hud)

            # Phụ đề đồng bộ thời gian
            if vo_words:
                prog = f_idx / float(max(1, total_frames))
                curr_w_idx = min(len(vo_words) - 1, int(prog * len(vo_words)))
                start_w = max(0, curr_w_idx - 3)
                chunk = " ".join(vo_words[start_w : start_w + 7])
                draw.rounded_rectangle((140, 595, 1140, 665), radius=12, fill=(0, 0, 0, 200))
                draw.text((180, 610), chunk, fill=(250, 204, 21), font=f_sub)

            proc.stdin.write(frame.convert("RGB").tobytes())

        proc.stdin.close()
        proc.wait(timeout=45)
        return out_mp4.exists() and out_mp4.stat().st_size > 1000
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        return False


def generate_talking_head_clip(
    scene: dict,
    visual: VisualSceneOutput,
    voice_out: Optional[VoiceSceneOutput],
    duration_sec: float,
    out_mp4: Path,
    force_local: bool = False,
) -> str:
    """Điều phối tạo clip nhân vật nói chuyện khớp tiếng (Muse Lip-Sync -> Local MuseTalk -> Audio-Reactive Talking HUD)."""
    img_path = Path(visual.base_image_path)
    wav_path = Path(voice_out.audio_path) if voice_out and voice_out.audio_path else Path("")

    if not force_local:
        cloud_or_local = _try_muse_or_cloud_lipsync(img_path, wav_path, duration_sec, out_mp4)
        if cloud_or_local:
            return cloud_or_local

    ok = _render_audio_reactive_talking_head(scene, visual, voice_out, duration_sec, out_mp4, fps=30)
    return "audio_reactive_talking_head" if ok else "talking_head_fallback"
