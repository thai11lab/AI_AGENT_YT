"""Unit tests cho Muse Video-Gen & Talking-Head Lip-Sync Adapter + GTA Niche Visual Pack."""
import math
import struct
import wave
from pathlib import Path

from agent_04_motion_broll.motion_engine import _extract_broll_query, render_scene_motion
from agent_04_motion_broll.muse_video_adapter import extract_wav_rms_envelope
from core.schemas import SceneItem
from PIL import Image
from shared.contracts import VisualSceneOutput, VoiceSceneOutput


def _make_test_wav(path: Path, dur_sec: float = 2.0, sr: int = 24000) -> None:
    n = int(dur_sec * sr)
    buf = bytearray()
    for i in range(n):
        t = i / sr
        val = int(12000 * math.sin(2 * math.pi * 220 * t) * (0.5 + 0.5 * math.sin(2 * math.pi * 2 * t)))
        buf.extend(struct.pack("<h", val))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(buf))


def test_talking_head_schema_and_gta_broll_query():
    sc = SceneItem(
        scene_id="S001",
        visual_mode="LIPSYNC_AVATAR",
        voiceover_text="For ten years players drove past this rusty power station in East Los Santos without looking twice.",
        flux_base_image_prompt=(
            "A stylized GTA character detective standing in front of an abandoned power station in East Los Santos at night, "
            "35mm lens, dramatic neon streetlamp lighting, shallow depth of field, cinematic framing."
        ),
    )
    assert sc.visual_mode == "TALKING_HEAD"

    q = _extract_broll_query(sc.model_dump())
    assert "gta" in q.lower()


def test_extract_wav_rms_and_render_talking_head_clip(tmp_path: Path):
    wav_path = tmp_path / "voice.wav"
    _make_test_wav(wav_path, dur_sec=2.0)

    env = extract_wav_rms_envelope(wav_path, fps=30)
    assert len(env) >= 55
    assert max(env) == 1.0
    assert min(env) >= 0.0

    img_path = tmp_path / "gta_char.png"
    Image.new("RGB", (1280, 720), (35, 25, 65)).save(img_path)

    vis = VisualSceneOutput(
        scene_id="S001",
        visual_mode="TALKING_HEAD",
        base_image_path=str(img_path),
        provider_used="test_mock",
    )
    voice = VoiceSceneOutput(scene_id="S001", audio_path=str(wav_path), duration_sec=2.0, engine_used="omnivoice")
    scene = {
        "scene_id": "S001",
        "visual_mode": "TALKING_HEAD",
        "camera_move": "SLOW_PUSH_IN",
        "voiceover_text": "Look at this scratched serial number inside the abandoned Los Santos room.",
    }

    m_out = render_scene_motion(scene, vis, duration_sec=2.0, out_dir=tmp_path / "motion", force_local=True, voice_out=voice)
    assert m_out.motion_engine == "audio_reactive_talking_head"
    assert Path(m_out.video_clip_path).exists()
    assert Path(m_out.video_clip_path).stat().st_size > 10000
