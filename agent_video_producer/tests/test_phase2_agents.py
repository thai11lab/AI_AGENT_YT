"""Kiểm thử toàn diện 4 AI Agent của Giai đoạn 2 (agent_voice, agent_visual, agent_motion, agent_compositor)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from run_phase2 import run_phase2_pipeline  # noqa: E402
from shared.channels import get_channel_persona  # noqa: E402
from shared.contracts import Phase2Manifest  # noqa: E402


def test_channel_persona_registry():
    us = get_channel_persona("med_forensic_us", "en")
    uk = get_channel_persona("dark_history_uk", "en")
    vn = get_channel_persona("dieu_tra_vn", "vi")
    assert us.edge_voice != uk.edge_voice
    assert vn.market_lang == "vi"
    assert us.emotion_exaggeration > 0.5


def test_phase2_four_agents_end_to_end(tmp_path):
    # Tạo một gói production_package mẫu gồm 2 cảnh (AI_VIDEO + DOCUMENT_HIGHLIGHT)
    pkg = tmp_path / "run-test-phase2"
    pkg.mkdir(parents=True)

    master_script = {
        "schema_version": "3.1",
        "run_id": "run-test-phase2",
        "language": "en",
        "source_rival_url": "https://youtube.com/watch?v=test",
        "scenes": [
            {
                "scene_id": "S001",
                "act_number": 1,
                "narrative_phase": "HOOK",
                "visual_mode": "AI_VIDEO",
                "voiceover_text": "The frantic monitor flatlined inside the cold emergency room.",
                "flux_base_image_prompt": "Wide shot of an emergency room monitor flatlining in cold blue light, 35mm lens.",
                "camera_move": "SLOW_PUSH_IN",
                "parallax_spec": {
                    "foreground_isolated": "IV stand",
                    "midground_main": "Flatline monitor",
                    "background_plate": "Dark ICU wall",
                },
                "audio_cues": [{"sfx_category": "FLATLINE", "trigger_word": "flatlined", "volume_db": -6.0}],
                "evidence_refs": ["EV_001"],
            },
            {
                "scene_id": "S002",
                "act_number": 2,
                "narrative_phase": "SETUP",
                "visual_mode": "DOCUMENT_HIGHLIGHT",
                "voiceover_text": "Hospital records revealed a critical discrepancy in the official timestamp.",
                "flux_base_image_prompt": "Close up of hospital record document on desk, 35mm lens.",
                "camera_move": "SLOW_PUSH_IN",
                "document_asset": {
                    "source_url": "https://pubmed.ncbi.nlm.nih.gov/",
                    "page": 1,
                    "highlight_text": "Declaration of death preceded consent by four minutes",
                },
                "audio_cues": [{"sfx_category": "IMPACT", "trigger_word": "discrepancy", "volume_db": -6.0}],
                "evidence_refs": ["EV_001"],
            },
        ],
    }
    evidence = [
        {
            "evidence_id": "EV_001",
            "factual_claim": "Hospital timestamp preceded organ referral consent.",
            "verbatim_quote": "Declaration of death preceded consent by four minutes",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/",
        }
    ]

    (pkg / "master_script.json").write_text(json.dumps(master_script), encoding="utf-8")
    (pkg / "evidence_dossier.json").write_text(json.dumps(evidence), encoding="utf-8")

    final_mp4 = run_phase2_pipeline(pkg, channel_id="med_forensic_us", max_scenes=2, force_local=True)
    assert final_mp4.exists()
    assert final_mp4.with_suffix(".srt").exists()

    manifest_file = pkg / "phase2_output" / "phase2_manifest.json"
    assert manifest_file.exists()
    manifest = Phase2Manifest.model_validate_json(manifest_file.read_text(encoding="utf-8"))
    assert "S001" in manifest.voice_outputs
    assert "S002" in manifest.visual_outputs
    assert "S001" in manifest.motion_outputs
    assert manifest.voice_outputs["S001"].trigger_timestamps.get("flatlined", 0) > 0
