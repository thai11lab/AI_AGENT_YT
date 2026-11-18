"""Agent 2: Visual Studio Agent (agent_visual).
Sinh tài sản hình ảnh 16:9 (1280x720) cho từng cảnh bằng Pillow (PIL) độ nét cao + Cloud API (Flux):
1. DOCUMENT_HIGHLIGHT: Trang hồ sơ tài liệu thật, đóng dấu pháp y + bút dạ quang vàng ($0).
2. KINETIC_DATA_CARD: Bảng số liệu điều tra độ tương phản cao ($0).
3. AI_VIDEO & STATIC_PARALLAX:
   - Cloud API: Gọi Flux.1-dev / Flux.1-schnell qua Fal.ai hoặc 370.ai/OpenAI.
   - Local Cinema Renderer ($0): Vẽ bằng Pillow với ánh sáng Spotlight 35mm, lưới chiều sâu, sóng sinh học/hồ sơ và hạt phim Kodak 5219.
"""
import math
import random
import textwrap
from pathlib import Path
from typing import Dict, Optional

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from shared.channels import ChannelPersona
from shared.contracts import VisualSceneOutput
from shared.env import get_env_key


def _load_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if mono:
        candidates = [
            "/System/Library/Fonts/Menlo.ttc",
            "/System/Library/Fonts/Monaco.ttf",
            "/Library/Fonts/Courier New.ttf",
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
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(h: str, default=(15, 34, 46)) -> tuple[int, int, int]:
    s = h.lstrip("#")
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except Exception:
            pass
    return default


def _call_fal_flux(prompt: str, out_png: Path, is_premium: bool = False) -> bool:
    fal_key = get_env_key("FAL_API_KEY") or get_env_key("FAL_KEY")
    if not fal_key:
        return False
    endpoint = "https://fal.run/fal-ai/flux/dev" if is_premium else "https://fal.run/fal-ai/flux/schnell"
    payload = {
        "prompt": prompt,
        "image_size": "landscape_16_9",
        "num_inference_steps": 24 if is_premium else 4,
    }
    headers = {"Authorization": f"Key {fal_key}", "Content-Type": "application/json"}
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
            if resp.status_code >= 400:
                return False
            images = resp.json().get("images") or []
            if not images or not images[0].get("url"):
                return False
            out_png.write_bytes(client.get(images[0]["url"]).content)
            return True
    except Exception:
        return False


def _call_pollinations_flux(prompt: str, out_png: Path, seed: int = 42) -> bool:
    """Tải ảnh AI 35mm thật hoàn toàn miễn phí qua Pollinations Flux endpoint (không cần API key)."""
    from urllib.parse import quote

    clean_p = f"{prompt[:380]}, photorealistic 35mm documentary still frame, dramatic lighting, Kodak 5219 film grain, no text"
    url = f"https://image.pollinations.ai/prompt/{quote(clean_p)}?width=1280&height=720&model=flux&nologo=true&seed={seed}"
    try:
        with httpx.Client(timeout=35.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200 and len(resp.content) > 8000:
                out_png.parent.mkdir(parents=True, exist_ok=True)
                out_png.write_bytes(resp.content)
                return True
    except Exception:
        pass
    return False


def _call_openai_compat_image(prompt: str, out_png: Path) -> bool:
    api_key = get_env_key("OPENAI_API_KEY")
    base_url = get_env_key("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key or "api.openai.com" in base_url:
        return False
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "flux-schnell", "prompt": prompt, "size": "1280x720", "n": 1}
    try:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(f"{base_url.rstrip('/')}/images/generations", headers=headers, json=payload)
            if resp.status_code >= 400:
                return False
            data = resp.json().get("data") or []
            if not data or not data[0].get("url"):
                return False
            out_png.write_bytes(client.get(data[0]["url"]).content)
            return True
    except Exception:
        return False


def _render_document_plate_pil(scene: dict, out_png: Path, evidence_map: Dict[str, dict]) -> None:
    """Vẽ trang hồ sơ pháp y/khoa học thật kèm bút dạ quang vàng bằng Pillow."""
    w, h = 1280, 720
    img = Image.new("RGB", (w, h), (10, 15, 22))
    draw = ImageDraw.Draw(img, "RGBA")

    doc = scene.get("document_asset") or {}
    ev_refs = scene.get("evidence_refs") or ["EV_001"]
    ev_id = ev_refs[0] if ev_refs else "EV_001"
    ev_item = evidence_map.get(ev_id, {})

    src_url = str(doc.get("source_url") or ev_item.get("source_url") or "https://pubmed.ncbi.nlm.nih.gov")[:75]
    hl_text = str(doc.get("highlight_text") or ev_item.get("verbatim_quote") or scene.get("voiceover_text", ""))
    claim_text = str(ev_item.get("factual_claim") or scene.get("voiceover_text", ""))

    # Tờ giấy hồ sơ
    draw.rounded_rectangle((130, 50, 1150, 670), radius=8, fill=(244, 241, 232, 255), outline=(180, 175, 160, 255), width=2)
    draw.rectangle((130, 50, 1150, 112), fill=(22, 32, 48, 255))

    f_header = _load_font(22, bold=True, mono=True)
    f_body = _load_font(24, bold=True)
    f_sub = _load_font(19)
    f_mono = _load_font(16, mono=True)

    draw.text((160, 68), f"CLASSIFIED FORENSIC DOSSIER // EXHIBIT {ev_id}", fill=(248, 250, 252), font=f_header)
    draw.text((940, 72), "DECLASSIFIED", fill=(239, 68, 68), font=f_header)

    # Các dòng văn bản mờ & bị bôi đen (redacted bars)
    for y_bar, bar_w in [(145, 580), (175, 840), (205, 420)]:
        draw.rectangle((170, y_bar, 170 + bar_w, y_bar + 16), fill=(203, 213, 225, 255))
    draw.rectangle((620, 205, 890, 221), fill=(15, 23, 42, 255))

    # Vùng tô sáng dạ quang vàng (Yellow Highlighter)
    wrapped_hl = textwrap.wrap(hl_text, width=58)[:3]
    hl_box_h = max(85, len(wrapped_hl) * 36 + 28)
    draw.rounded_rectangle((160, 255, 1120, 255 + hl_box_h), radius=6, fill=(253, 224, 71, 215), outline=(234, 179, 8, 255), width=2)

    for i, line in enumerate(wrapped_hl):
        draw.text((180, 270 + i * 34), line, fill=(15, 23, 42), font=f_body)

    # Nội dung tóm tắt bằng chứng bên dưới
    wrapped_claim = textwrap.wrap(f"Forensic Finding: {claim_text}", width=68)[:3]
    for i, line in enumerate(wrapped_claim):
        draw.text((170, 420 + i * 30), line, fill=(51, 65, 85), font=f_sub)

    draw.line((165, 595, 1115, 595), fill=(203, 213, 225), width=2)
    draw.text((170, 615), f"PRIMARY SOURCE: {src_url}", fill=(71, 85, 105), font=f_mono)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")


def _render_kinetic_card_pil(scene: dict, out_png: Path, persona: ChannelPersona) -> None:
    """Vẽ thẻ dữ liệu điều tra độ tương phản cao (KINETIC_DATA_CARD)."""
    w, h = 1280, 720
    tint = _hex_to_rgb(persona.color_tint_hex, (12, 34, 46))
    acc = _hex_to_rgb(persona.accent_hex, (245, 158, 11))

    img = Image.new("RGB", (w, h), tint)
    draw = ImageDraw.Draw(img, "RGBA")

    for x in range(0, w, 64):
        draw.line((x, 0, x, h), fill=(255, 255, 255, 14), width=1)
    for y in range(0, h, 64):
        draw.line((0, y, w, y), fill=(255, 255, 255, 14), width=1)

    draw.rounded_rectangle((140, 130, 1140, 590), radius=12, fill=(7, 11, 18, 235), outline=(acc[0], acc[1], acc[2], 180), width=2)
    draw.rectangle((140, 130, 1140, 142), fill=(acc[0], acc[1], acc[2], 255))

    f_tag = _load_font(20, bold=True, mono=True)
    f_big = _load_font(48, bold=True)
    f_sub = _load_font(24)

    ev_str = ", ".join(scene.get("evidence_refs") or ["VERIFIED METRIC"])
    draw.text((190, 175), f"FORENSIC TELEMETRY // {ev_str}", fill=(148, 163, 184), font=f_tag)

    headline = str(scene.get("on_screen_text") or "CRITICAL DATA ANOMALY")
    for i, line in enumerate(textwrap.wrap(headline, width=30)[:2]):
        draw.text((190, 245 + i * 60), line, fill=acc, font=f_big)

    vo_lines = textwrap.wrap(scene.get("voiceover_text", ""), width=56)[:3]
    for i, line in enumerate(vo_lines):
        draw.text((190, 410 + i * 36), line, fill=(226, 232, 240), font=f_sub)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")


def _render_cinema_plate_pil(scene: dict, out_png: Path, persona: ChannelPersona) -> None:
    """Vẽ khung hình điện ảnh 35mm noir có chiều sâu không gian, sóng sinh học & thông tin đạo diễn bằng Pillow."""
    w, h = 1280, 720
    tint = _hex_to_rgb(persona.color_tint_hex, (12, 34, 46))
    acc = _hex_to_rgb(persona.accent_hex, (56, 189, 248))

    img = Image.new("RGB", (w, h), (5, 8, 13))
    draw = ImageDraw.Draw(img, "RGBA")

    # Vầng sáng Spotlight điện ảnh ở trung tâm
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for r in range(520, 40, -25):
        alpha = int(38 * (1 - r / 520.0))
        ov_draw.ellipse((640 - r * 1.3, 330 - r * 0.85, 640 + r * 1.3, 330 + r * 0.85), fill=(tint[0] + 25, tint[1] + 45, tint[2] + 60, alpha))
    overlay = overlay.filter(ImageFilter.GaussianBlur(radius=18))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
    draw = ImageDraw.Draw(img, "RGBA")

    # Lưới chiều sâu thị giác
    for x in range(0, w, 80):
        draw.line((x, 70, x, 650), fill=(255, 255, 255, 10), width=1)
    for y in range(70, 650, 80):
        draw.line((0, y, w, y), fill=(255, 255, 255, 10), width=1)

    # Vẽ sóng điện tâm đồ / điện não đồ (ECG / cEEG waveform) tạo điểm nhấn chuyển động khi zoompan
    sid = scene.get("scene_id", "S001")
    seed_num = int(sid[1:]) if sid[1:].isdigit() else 1
    rng = random.Random(seed_num)
    pts = []
    for x in range(90, 1190, 8):
        norm_x = (x - 90) / 1100.0
        spike = math.sin(norm_x * math.pi * (6 + seed_num % 5)) * math.exp(-((norm_x - 0.48) ** 2) * 18)
        y = int(285 + spike * 95 + rng.uniform(-4, 4))
        pts.append((x, y))
    if len(pts) > 2:
        draw.line(pts, fill=(acc[0], acc[1], acc[2], 195), width=3)

    # Khung thông tin trung cảnh (Midground Focal Card)
    ps = scene.get("parallax_spec") or {}
    mid_desc = str(ps.get("midground_main") or scene.get("flux_base_image_prompt", ""))
    fg_desc = str(ps.get("foreground_isolated") or "35mm shallow depth foreground")
    bg_desc = str(ps.get("background_plate") or "Atmospheric noir environment")

    draw.rounded_rectangle((110, 360, 1170, 565), radius=10, fill=(6, 10, 16, 210), outline=(255, 255, 255, 35), width=1)
    draw.rectangle((110, 360, 118, 565), fill=(acc[0], acc[1], acc[2], 255))

    f_hud = _load_font(17, bold=True, mono=True)
    f_main = _load_font(28, bold=True)
    f_meta = _load_font(18, mono=True)

    phase = scene.get("narrative_phase", "HOOK")
    cam = scene.get("camera_move", "SLOW_PUSH_IN")
    ev_refs = ", ".join(scene.get("evidence_refs") or ["ARCHIVE"])

    # Thanh Cinema Letterbox trên/dưới + HUD góc máy
    draw.rectangle((0, 0, w, 64), fill=(0, 0, 0, 230))
    draw.rectangle((0, 656, w, h), fill=(0, 0, 0, 230))
    draw.text((40, 22), f"REC ● {sid} // ACT {scene.get('act_number', 1)} ({phase}) // CAM: {cam}", fill=acc, font=f_hud)
    draw.text((940, 22), f"DOSSIER: {ev_refs}", fill=(148, 163, 184), font=f_hud)

    for i, line in enumerate(textwrap.wrap(mid_desc.upper(), width=54)[:2]):
        draw.text((145, 385 + i * 38), line, fill=(248, 250, 252), font=f_main)

    draw.text((145, 485), f"FG LAYER : {fg_desc[:65]}", fill=(148, 163, 184), font=f_meta)
    draw.text((145, 515), f"BG PLATE : {bg_desc[:65]}", fill=(100, 116, 139), font=f_meta)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")


def generate_scene_visual(
    scene: dict,
    out_dir: Path,
    persona: ChannelPersona,
    evidence_map: Optional[Dict[str, dict]] = None,
    force_local: bool = False,
) -> VisualSceneOutput:
    """Sinh ảnh gốc 1280x720 cho 1 cảnh theo đúng visual_mode."""
    out_dir.mkdir(parents=True, exist_ok=True)
    sid = scene["scene_id"]
    mode = scene.get("visual_mode", "STATIC_PARALLAX")
    out_png = out_dir / f"{sid}.png"
    ev_map = evidence_map or {}

    if mode == "DOCUMENT_HIGHLIGHT":
        _render_document_plate_pil(scene, out_png, ev_map)
        return VisualSceneOutput(scene_id=sid, visual_mode=mode, base_image_path=str(out_png), provider_used="pil_document_renderer")

    if mode == "KINETIC_DATA_CARD":
        _render_kinetic_card_pil(scene, out_png, persona)
        return VisualSceneOutput(scene_id=sid, visual_mode=mode, base_image_path=str(out_png), provider_used="pil_kinetic_renderer")

    prompt = scene.get("flux_base_image_prompt", "")
    is_prem = (scene.get("narrative_phase") == "HOOK") or bool(scene.get("reference_entities"))
    seed_val = int(sid[1:]) if sid[1:].isdigit() else 42
    provider_used = "pil_35mm_cinema_plate"

    if not force_local:
        if _call_fal_flux(prompt, out_png, is_premium=is_prem):
            provider_used = "fal_flux_dev" if is_prem else "fal_flux_schnell"
        elif _call_openai_compat_image(prompt, out_png):
            provider_used = "openai_compat_flux"
        elif _call_pollinations_flux(prompt, out_png, seed=seed_val):
            provider_used = "pollinations_flux_35mm"
        else:
            _render_cinema_plate_pil(scene, out_png, persona)
    else:
        _render_cinema_plate_pil(scene, out_png, persona)

    return VisualSceneOutput(scene_id=sid, visual_mode=mode, base_image_path=str(out_png), provider_used=provider_used)
