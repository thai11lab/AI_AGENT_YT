"""N8 (code thuần): tính thời lượng/ thời điểm bắt đầu và kiểm tra ngân sách Hybrid Motion."""
from typing import Dict, List

from core.schemas import MasterScript, NARRATOR_WPM, MAX_AI_VIDEO_CLIP_SEC

HOOK_END_SEC = 60.0
BODY_AI_MAX_SHARE = 0.20      # trần theo THỜI LƯỢNG ở thân video
HOOK_AI_MIN_SHARE = 0.95


def finalize_timing(script: MasterScript) -> MasterScript:
    """Điền duration_sec, start_sec, video_duration_sec (ước tính)."""
    wpm = NARRATOR_WPM[script.language]
    t = 0.0
    for s in script.scenes:
        if s.duration_source == "estimated":
            s.duration_sec = round(len(s.voiceover_text.split()) / wpm * 60 + s.pause_after_sec, 2)
        s.start_sec = round(t, 2)
        t += s.duration_sec
        if s.visual_mode == "AI_VIDEO":
            s.video_duration_sec = round(min(s.duration_sec, script.output_spec.max_ai_clip_sec), 2)
    script.estimated_total_duration_sec = round(t, 2)
    return script


def over_clip_limit(script: MasterScript) -> List[str]:
    """Cảnh AI_VIDEO dài hơn giới hạn clip: cần tách cảnh hoặc đổi chế độ."""
    lim = script.output_spec.max_ai_clip_sec
    return [s.scene_id for s in script.scenes if s.visual_mode == "AI_VIDEO" and s.duration_sec > lim]


def budget_report(script: MasterScript) -> Dict:
    hook = [s for s in script.scenes if s.narrative_phase == "HOOK"]
    body = [s for s in script.scenes if s.narrative_phase != "HOOK"]
    hook_total = sum(s.duration_sec for s in hook) or 1e-9
    body_total = sum(s.duration_sec for s in body) or 1e-9
    hook_ai = sum(s.duration_sec for s in hook if s.visual_mode == "AI_VIDEO") / hook_total
    mix = {m: round(sum(s.duration_sec for s in body if s.visual_mode == m) / body_total, 3)
           for m in ("AI_VIDEO", "TALKING_HEAD", "STATIC_PARALLAX", "DOCUMENT_HIGHLIGHT", "KINETIC_DATA_CARD")}
    return {
        "total_duration_sec": script.estimated_total_duration_sec,
        "scene_count": len(script.scenes),
        "hook_duration_sec": round(sum(s.duration_sec for s in hook), 1),
        "hook_len_ok": 50.0 <= sum(s.duration_sec for s in hook) <= 70.0,
        "hook_ai_share": round(hook_ai, 3),
        "hook_ai_ok": hook_ai >= HOOK_AI_MIN_SHARE,
        "body_mix_by_duration": mix,
        "body_ai_ok": mix["AI_VIDEO"] <= BODY_AI_MAX_SHARE,
        "ai_video_clips": sum(1 for s in script.scenes if s.visual_mode == "AI_VIDEO"),
        "scenes_over_clip_limit": over_clip_limit(script),
    }
