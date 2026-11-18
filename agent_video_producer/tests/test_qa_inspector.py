"""Unit tests cho Agent 06: Output Video & Anti-Repetition QA Inspector."""
from pathlib import Path

from unittest.mock import MagicMock, patch

from agent_06_qa_inspector.qa_inspector import (
    audit_final_video,
    audit_srt_file,
    deduplicate_and_audit_scenes,
    text_similarity_jaccard,
)
from shared.alerts import scan_all_projects, send_discord_alert, write_live_status
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


def test_audit_srt_file_valid_and_overlap(tmp_path: Path):
    srt_ok = tmp_path / "ok.srt"
    srt_ok.write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nLine one\n\n2\n00:00:02,100 --> 00:00:04,000\nLine two\n",
        encoding="utf-8",
    )
    res_ok = audit_srt_file(srt_ok)
    assert res_ok["ok"] is True
    assert res_ok["blocks"] == 2
    assert res_ok["overlaps"] == 0

    srt_bad = tmp_path / "bad.srt"
    srt_bad.write_text(
        "1\n00:00:00,000 --> 00:00:03,000\nLine one\n\n2\n00:00:02,000 --> 00:00:04,000\nOverlap\n",
        encoding="utf-8",
    )
    res_bad = audit_srt_file(srt_bad)
    assert res_bad["ok"] is False
    assert res_bad["overlaps"] == 1


def test_live_status_and_scan_all_projects_with_thumbnail(tmp_path: Path):
    pkg = tmp_path / "run-test-001"
    pkg.mkdir()
    (pkg / "master_script.json").write_text('{"run_id": "run-test-001", "language": "vi", "scenes": [{"scene_id": "S001"}, {"scene_id": "S002"}]}', encoding="utf-8")
    vis_dir = pkg / "phase2_output" / "visual"
    vis_dir.mkdir(parents=True)
    (vis_dir / "S001.png").write_bytes(b"fake_png_bytes")

    write_live_status(pkg, "RUNNING", "Agent 04: Motion", "S001", done_scenes=1, total_scenes=2, channel_id="ch20_dieu_tra_vn")
    projects = scan_all_projects(tmp_path)
    assert len(projects) == 1
    assert projects[0]["status"] == "RUNNING"
    assert projects[0]["progress_pct"] == 50.0
    assert projects[0]["thumbnail_path"].endswith("S001.png")


def test_send_discord_alert_posts_embed():
    mock_resp = MagicMock()
    mock_resp.status = 204
    mock_resp.__enter__.return_value = mock_resp
    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
        ok, detail = send_discord_alert(
            webhook_url="https://discord.com/api/webhooks/test/token",
            title="Test Error",
            message="Something failed",
            level="error",
        )
        assert ok is True
        assert "204" in detail
        assert mock_open.called
