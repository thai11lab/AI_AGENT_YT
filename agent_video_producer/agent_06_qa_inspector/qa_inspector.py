"""Agent 06: Output Video & Anti-Repetition QA Inspector (agent_qa_inspector).
Nhiệm vụ kiểm định độc lập trước khi bàn giao video:
1. Anti-Repetition Audit: Quét toàn bộ lời thoại (voiceover_text) bằng Jaccard Word & Bigram Similarity để phát hiện và loại bỏ các cảnh bị đọc lặp lại nội dung (VD: S004 lặp lại nguyên văn ở S011).
2. Video & Audio Sync Audit: Dùng ffprobe kiểm tra file .mp4 đầu ra (luồng Video + Audio, độ lệch thời lượng so với tổng thời lượng các file .wav để phát hiện mất từ/mất cảnh, kiểm tra file rỗng).
3. Subtitle Audit: Kiểm tra file .srt có đủ số dòng và không bị lệch mốc thời gian.
4. Xuất báo cáo `qa_report.json` trong `phase2_output/`.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple

from shared.alerts import send_discord_alert
from shared.contracts import MotionSceneOutput, VoiceSceneOutput


def _tokens_and_bigrams(text: str) -> Tuple[Set[str], Set[str]]:
    words = re.findall(r"[^\W\d_]+", text.lower())
    w_set = {w for w in words if len(w) > 1}
    bigrams = {f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)}
    return w_set, bigrams


def text_similarity_jaccard(text_a: str, text_b: str) -> float:
    """Tính độ tương đồng ngữ nghĩa bề mặt (0.0 -> 1.0) kết hợp Word Jaccard (50%) + Bigram Jaccard (50%)."""
    wa, ba = _tokens_and_bigrams(text_a)
    wb, bb = _tokens_and_bigrams(text_b)
    if not wa or not wb:
        return 0.0
    w_jac = len(wa & wb) / float(len(wa | wb))
    b_jac = (len(ba & bb) / float(len(ba | bb))) if (ba and bb) else w_jac
    return round(0.5 * w_jac + 0.5 * b_jac, 3)


def deduplicate_and_audit_scenes(
    scenes: List[dict],
    similarity_threshold: float = 0.55,
    drop_duplicates: bool = True,
) -> Dict:
    """Quét và lọc các cảnh có nội dung lặp lại gần giống hoặc trùng nguyên văn."""
    kept: List[dict] = []
    duplicates_found: List[Dict] = []

    for sc in scenes:
        vo = str(sc.get("voiceover_text", "")).strip()
        sid = sc.get("scene_id", "S???")
        matched_with = None
        best_sim = 0.0

        # So sánh với tất cả các cảnh đã giữ lại (đặc biệt nhạy với các cảnh trong cùng 25 cảnh gần nhất)
        for prev in kept:
            sim = text_similarity_jaccard(vo, str(prev.get("voiceover_text", "")))
            if sim > best_sim:
                best_sim = sim
                matched_with = prev.get("scene_id", "S???")

        if best_sim >= similarity_threshold and matched_with:
            duplicates_found.append(
                {
                    "duplicate_scene_id": sid,
                    "original_scene_id": matched_with,
                    "similarity": best_sim,
                    "voiceover_preview": vo[:100],
                }
            )
            if not drop_duplicates:
                kept.append(sc)
        else:
            kept.append(sc)

    return {
        "input_scenes": len(scenes),
        "kept_scenes": len(kept),
        "duplicates_removed": len(duplicates_found) if drop_duplicates else 0,
        "duplicates": duplicates_found,
        "cleaned_scenes": kept,
    }


def _parse_srt_ts(ts: str) -> float:
    m = re.match(r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$", ts.strip())
    if not m:
        return -1.0
    h, mi, s, ms = (int(x) for x in m.groups())
    return h * 3600 + mi * 60 + s + ms / 1000.0


def audit_srt_file(srt_path: Path) -> Dict:
    """Kiểm tra cấu trúc file phụ đề .srt: số block, timestamp hợp lệ, và phát hiện chồng lấn."""
    if not srt_path.exists() or srt_path.stat().st_size <= 20:
        return {"ok": False, "blocks": 0, "overlaps": 0, "issues": ["Thiếu file phụ đề .srt hoặc file rỗng."]}

    raw = srt_path.read_text(encoding="utf-8", errors="ignore").strip()
    blocks = [b.strip() for b in re.split(r"\r?\n\r?\n+", raw) if b.strip()]
    issues: List[str] = []
    overlaps = 0
    prev_end = 0.0

    for idx, blk in enumerate(blocks, 1):
        lines = blk.splitlines()
        ts_line = next((ln for ln in lines if "-->" in ln), None)
        if not ts_line:
            issues.append(f"Block #{idx} thiếu dòng timestamp.")
            continue
        parts = ts_line.split("-->")
        if len(parts) != 2:
            issues.append(f"Block #{idx} sai định dạng timestamp.")
            continue
        start_s = _parse_srt_ts(parts[0])
        end_s = _parse_srt_ts(parts[1].split()[0])
        if start_s < 0 or end_s <= start_s:
            issues.append(f"Block #{idx} có mốc thời gian không hợp lệ ({ts_line.strip()}).")
            continue
        if start_s + 0.05 < prev_end:
            overlaps += 1
        prev_end = max(prev_end, end_s)

    if overlaps > 0:
        issues.append(f"Có {overlaps} cặp phụ đề bị chồng lấn mốc thời gian.")
    return {
        "ok": len(blocks) > 0 and len(issues) == 0,
        "blocks": len(blocks),
        "overlaps": overlaps,
        "issues": issues,
    }


def _ffprobe_streams_and_duration(mp4_path: Path) -> Dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not mp4_path.exists() or mp4_path.stat().st_size < 1000:
        return {"ok": False, "duration_sec": 0.0, "has_video": False, "has_audio": False}
    try:
        raw = subprocess.check_output(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(mp4_path)],
            timeout=15,
        ).decode("utf-8", errors="ignore")
        info = json.loads(raw)
        streams = info.get("streams") or []
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        has_v = v_stream is not None
        has_a = a_stream is not None
        dur = float((info.get("format") or {}).get("duration") or 0.0)
        return {
            "ok": has_v and has_a and dur > 0.5,
            "duration_sec": round(dur, 2),
            "has_video": has_v,
            "has_audio": has_a,
            "width": int(v_stream.get("width", 0)) if v_stream else 0,
            "height": int(v_stream.get("height", 0)) if v_stream else 0,
            "video_codec": v_stream.get("codec_name", "") if v_stream else "",
            "audio_codec": a_stream.get("codec_name", "") if a_stream else "",
        }
    except Exception:
        return {"ok": False, "duration_sec": 0.0, "has_video": False, "has_audio": False}


def audit_final_video(
    final_mp4: Path,
    scenes: List[dict],
    voice_outputs: Dict[str, VoiceSceneOutput],
    motion_outputs: Dict[str, MotionSceneOutput],
    out_report_path: Path,
    discord_webhook_url: str = "",
) -> Dict:
    """Kiểm định toàn diện video đầu ra: Chống lặp nội dung + Khớp thời lượng Audio/Video + Kiểm tra phụ đề .srt."""
    dup_audit = deduplicate_and_audit_scenes(scenes, similarity_threshold=0.55, drop_duplicates=False)
    probe = _ffprobe_streams_and_duration(final_mp4)

    expected_voice_dur = round(sum(voice_outputs[s["scene_id"]].duration_sec for s in scenes if s["scene_id"] in voice_outputs), 2)
    actual_dur = probe["duration_sec"]
    sync_drift_sec = round(abs(actual_dur - expected_voice_dur), 2) if actual_dur > 0 else expected_voice_dur

    empty_clips = [
        sid for sid, m in motion_outputs.items() if not Path(m.video_clip_path).exists() or Path(m.video_clip_path).stat().st_size < 1000
    ]

    srt_path = final_mp4.with_suffix(".srt")
    srt_audit = audit_srt_file(srt_path)
    srt_ok = srt_audit["ok"]

    warnings: List[str] = []
    if dup_audit["duplicates"]:
        warnings.append(f"Phát hiện {len(dup_audit['duplicates'])} cảnh bị lặp/trùng nội dung lời thoại.")
    if empty_clips:
        warnings.append(f"Có {len(empty_clips)} clip hình ảnh bị rỗng/lỗi: {empty_clips[:5]}")
    if expected_voice_dur > 0 and sync_drift_sec > max(5.0, len(scenes) * 0.15):
        warnings.append(f"Độ lệch thời lượng video ({actual_dur}s) vs tổng giọng nói ({expected_voice_dur}s) = {sync_drift_sec}s.")
    if not probe["ok"]:
        warnings.append("File MP4 đầu ra thiếu luồng Video hoặc Audio hợp lệ.")
    if not srt_ok:
        warnings.extend(srt_audit["issues"] or ["Thiếu file phụ đề .srt đi kèm."])

    status = "PASSED" if not warnings else "WARNING"
    report = {
        "qa_status": status,
        "final_mp4": str(final_mp4),
        "file_size_mb": round(final_mp4.stat().st_size / (1024 * 1024), 2) if final_mp4.exists() else 0.0,
        "video_probe": probe,
        "expected_voice_duration_sec": expected_voice_dur,
        "actual_video_duration_sec": actual_dur,
        "sync_drift_sec": sync_drift_sec,
        "srt_exists": srt_path.exists() and srt_path.stat().st_size > 20,
        "srt_audit": srt_audit,
        "empty_motion_clips": empty_clips,
        "duplicate_scenes_detected": dup_audit["duplicates"],
        "warnings": warnings,
    }

    out_report_path.parent.mkdir(parents=True, exist_ok=True)
    out_report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if status != "PASSED":
        send_discord_alert(
            webhook_url=discord_webhook_url,
            title=f"⚠️ Agent QA {status}: {final_mp4.name}",
            message="\n".join(f"• {w}" for w in warnings),
            level="warning",
            fields=[
                {"name": "Sync Drift", "value": f"{sync_drift_sec}s"},
                {"name": "Empty Clips", "value": str(len(empty_clips))},
                {"name": "SRT Blocks", "value": str(srt_audit.get("blocks", 0))},
            ],
        )

    return report
