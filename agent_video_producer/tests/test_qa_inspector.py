"""Unit tests cho Agent 06: Output Video & Anti-Repetition QA Inspector."""
from pathlib import Path

from agent_06_qa_inspector.qa_inspector import (
    audit_final_video,
    deduplicate_and_audit_scenes,
    text_similarity_jaccard,
)
from shared.contracts import MotionSceneOutput, VoiceSceneOutput


def test_deduplicate_and_audit_scenes_catches_gta_duplicates():
    scenes = [
        {
            "scene_id": "S001",
            "voiceover_text": "Vào năm hai nghìn mười lăm, FiveM ra đời như một nền tảng modding cho Grand Theft Auto V.",
        },
        {
            "scene_id": "S004",
            "voiceover_text": "Những người sáng tạo chính của FiveM bị cấm. Một động thái mạnh mẽ từ Take-Two khiến cộng đồng hoang mang.",
        },
        {
            "scene_id": "S011",
            "voiceover_text": "Những người sáng tạo chính của FiveM bị cấm. Một động thái mạnh mẽ từ Take-Two khiến cộng đồng hoang mang.",
        },
    ]

    sim = text_similarity_jaccard(scenes[1]["voiceover_text"], scenes[2]["voiceover_text"])
    assert sim >= 0.99

    res = deduplicate_and_audit_scenes(scenes, similarity_threshold=0.55, drop_duplicates=True)
    assert res["input_scenes"] == 3
    assert res["kept_scenes"] == 2
    assert res["duplicates_removed"] == 1
    assert res["duplicates"][0]["duplicate_scene_id"] == "S011"
    assert res["duplicates"][0]["original_scene_id"] == "S004"


def test_audit_final_video_detects_missing_mp4_and_writes_report(tmp_path: Path):
    mp4 = tmp_path / "final_documentary.mp4"
    mp4.write_bytes(b"")  # giả lập file lỗi
    report_path = tmp_path / "qa_report.json"

    scenes = [{"scene_id": "S001", "voiceover_text": "Test scene one."}]
    voices = {"S001": VoiceSceneOutput(scene_id="S001", audio_path="a.wav", duration_sec=4.0, engine_used="omnivoice")}
    motions = {"S001": MotionSceneOutput(scene_id="S001", video_clip_path="v.mp4", duration_sec=4.0, motion_engine="local_25d_parallax")}

    rep = audit_final_video(mp4, scenes, voices, motions, report_path)
    assert rep["qa_status"] == "WARNING"
    assert report_path.exists()
    assert len(rep["warnings"]) >= 1
