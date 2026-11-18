"""Sinh samples/master_script.sample.json (DỮ LIỆU GIẢ, chỉ để Phase 2 chạy thử hợp đồng).

Chạy:  python scripts/make_sample.py [en|vi]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import MasterScript  # noqa: E402
from core.timing import finalize_timing, budget_report  # noqa: E402

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"

STYLE = ("cinematic documentary still, 35mm lens, shallow depth of field, cold teal and amber color grade, "
         "fine film grain, practical lighting, photorealistic, no text overlay")
CLERK = "a tired middle-aged clerk in a grey cardigan and wire-rimmed glasses"
PRINTER = "a beige 1990s office laser printer with a blinking red warning LED"
OFFICE = "a windowless basement records office with fluorescent tube lights and steel shelving"

VO = {
    "en": [
        "At eleven forty seven the printer jammed. Nobody looked up.",
        "Behind the glass, the clerk kept typing, as if nothing happened.",
        "Then the red light began to blink, slowly, like a pulse.",
        "Everyone believed the story the first video told. The paper said otherwise.",
        "Page fifteen of the report held a serial number nobody had ever checked.",
        "The loss was four hundred twelve thousand dollars, logged in a single night.",
        "Three hours earlier, the same account had been quietly emptied.",
        "That is where the official timeline stops making sense.",
    ],
    "vi": [
        "Mười một giờ bốn mươi bảy, máy in kẹt giấy. Không ai ngẩng lên.",
        "Sau lớp kính, thư ký vẫn gõ phím, như chưa có gì xảy ra.",
        "Rồi đèn đỏ bắt đầu nhấp nháy, chậm rãi, như một nhịp mạch.",
        "Ai cũng tin câu chuyện của video đầu tiên. Nhưng trang giấy nói điều khác.",
        "Trang mười lăm của báo cáo ghi một số seri mà chưa ai từng kiểm tra lại.",
        "Khoản thiệt hại là bốn trăm mười hai nghìn đô la, ghi nhận chỉ trong một đêm.",
        "Ba giờ trước đó, chính tài khoản này đã lặng lẽ bị rút sạch.",
        "Đó là chỗ mà dòng thời gian chính thức bắt đầu vô nghĩa.",
    ],
}[LANG]
TRIG = {
    "en": ["jammed", "typing", "blink", "paper", "serial", "loss", "emptied", "timeline"],
    "vi": ["kẹt", "gõ", "nhấp", "trang", "seri", "thiệt", "rút", "dòng"],
}[LANG]
ONSCREEN = {"en": "$412,000", "vi": "412.000 USD"}[LANG]


def cue(i, cat="MECHANICAL_FOLEY"):
    return [{"sfx_category": cat, "trigger_word": TRIG[i], "volume_db": -8.0,
             "sfx_generation_prompt": "short realistic office sound effect, dry, no music"}]


def ai(i, act, phase, subj, move, motion):
    return {
        "scene_id": f"S{i + 1:03d}", "act_number": act, "narrative_phase": phase,
        "visual_mode": "AI_VIDEO", "voiceover_text": VO[i], "pause_after_sec": 0.2,
        "flux_base_image_prompt": f"{subj}, inside {OFFICE}, {STYLE}, dramatic low key lighting, "
                                  f"muted background details, tense atmosphere, wide aspect 16:9 framing",
        "negative_prompt": "text, watermark, logo, extra fingers, deformed hands, blurry",
        "reference_entities": ["CHAR_CLERK_01", "OBJ_PRINTER_01", "LOC_OFFICE_01"][: 2 if i else 3],
        "video_motion_prompt": motion, "camera_move": move, "premium_priority": 5 - min(i, 2),
        "parallax_spec": {"foreground_isolated": "blurred edge of a steel shelf or paper stack",
                          "midground_main": subj, "background_plate": "dim records office, fluorescent tubes"},
        "visual_bridge_from_prev": "cold open" if i == 0 else "continuous camera motion and matching red light",
        "audio_cues": cue(i), "evidence_refs": ["EV_001"],
    }


scenes = [
    ai(0, 1, "HOOK", f"close shot of {PRINTER} with paper crumpled in the tray", "SLOW_PUSH_IN",
       "slow push in on the jammed paper tray, red LED blinking"),
    ai(1, 1, "HOOK", f"{CLERK} typing behind a glass partition, reflection of fluorescent lights", "HANDHELD_TENSION",
       "subtle handheld sway, clerk keeps typing without looking up"),
    ai(2, 1, "HOOK", f"extreme close up of the red warning LED on {PRINTER}", "SLOW_PUSH_IN",
       "red LED pulses slowly, faint dust drifting in light"),
    {   # Parallax
        "scene_id": "S004", "act_number": 2, "narrative_phase": "SETUP",
        "visual_mode": "STATIC_PARALLAX", "voiceover_text": VO[3], "pause_after_sec": 0.3,
        "flux_base_image_prompt": f"wide shot of {CLERK} standing between steel shelves in {OFFICE}, {STYLE}, "
                                  f"stacks of cardboard archive boxes labeled with dates, dust in the air, "
                                  f"clear separation between foreground boxes and distant corridor",
        "negative_prompt": "text, watermark, logo, extra fingers",
        "reference_entities": ["CHAR_CLERK_01", "LOC_OFFICE_01"],
        "parallax_spec": {"foreground_isolated": "blurred archive boxes at the left edge",
                          "midground_main": "the clerk holding a thin folder",
                          "background_plate": "long dim corridor of steel shelving"},
        "visual_bridge_from_prev": "dissolve from red light to shelf warning lamp",
        "audio_cues": cue(3, "PAPER_SLIDE"), "evidence_refs": ["EV_002"],
    },
    {   # Document
        "scene_id": "S005", "act_number": 2, "narrative_phase": "SETUP",
        "visual_mode": "DOCUMENT_HIGHLIGHT", "voiceover_text": VO[4], "pause_after_sec": 0.3,
        "flux_base_image_prompt": f"top down macro of a printed technical report page on a wooden desk, {STYLE}, "
                                  f"a metal ruler and a coffee ring stain beside the page, soft desk lamp light, "
                                  f"sharp paper texture, placeholder for real document overlay",
        "reference_entities": [],
        "document_asset": {"source_url": "https://example.org/sample-report.pdf", "page": 15,
                           "highlight_text": "Serial No. 774-A"},
        "visual_bridge_from_prev": "camera tilts down from the folder to the open page",
        "audio_cues": cue(4, "PAPER_SLIDE"), "evidence_refs": ["EV_003"],
    },
    {   # Data card
        "scene_id": "S006", "act_number": 2, "narrative_phase": "ESCALATION",
        "visual_mode": "KINETIC_DATA_CARD", "voiceover_text": VO[5], "pause_after_sec": 0.3,
        "flux_base_image_prompt": f"dark textured concrete wall background with faint scratches, {STYLE}, "
                                  f"empty center area reserved for large typography, subtle vignette, "
                                  f"cold light from the top left, no visible letters or numbers anywhere",
        "reference_entities": [], "on_screen_text": ONSCREEN,
        "visual_bridge_from_prev": "hard cut on the beat",
        "audio_cues": cue(5, "SUB_BASS_HIT"), "evidence_refs": ["EV_004"],
    },
    {   # Parallax
        "scene_id": "S007", "act_number": 2, "narrative_phase": "ESCALATION",
        "visual_mode": "STATIC_PARALLAX", "voiceover_text": VO[6], "pause_after_sec": 0.3,
        "flux_base_image_prompt": f"medium shot of a glowing monitor showing a blank ledger window in {OFFICE}, {STYLE}, "
                                  f"a cold cup of tea and a ring of keys on the desk, blue screen light on the "
                                  f"clerk's empty chair, deep shadows in the background",
        "reference_entities": ["LOC_OFFICE_01"],
        "parallax_spec": {"foreground_isolated": "blurred keys on the desk edge",
                          "midground_main": "glowing monitor on the desk",
                          "background_plate": "dark shelving receding into shadow"},
        "visual_bridge_from_prev": "match cut: number card to monitor glow",
        "audio_cues": cue(6, "AMBIENT_ROOM"), "evidence_refs": ["EV_004"],
    },
    {   # Parallax
        "scene_id": "S008", "act_number": 2, "narrative_phase": "ESCALATION",
        "visual_mode": "STATIC_PARALLAX", "voiceover_text": VO[7], "pause_after_sec": 0.4,
        "flux_base_image_prompt": f"wide shot of a wall clock stopped at a quarter to midnight above {PRINTER}, {STYLE}, "
                                  f"paper strips on the floor, a single overhead tube light flickering, "
                                  f"cold shadows, strong sense of unresolved tension",
        "reference_entities": ["OBJ_PRINTER_01", "LOC_OFFICE_01"],
        "parallax_spec": {"foreground_isolated": "blurred paper strips on the floor",
                          "midground_main": "printer under the wall clock",
                          "background_plate": "dim office wall with a notice board"},
        "visual_bridge_from_prev": "round monitor glow to round wall clock",
        "audio_cues": cue(7, "TENSION_RISER"), "evidence_refs": ["EV_002", "EV_004"],
    },
]

plan = {
    "selected_hypothesis_id": "HYP_01",
    "viral_titles": [f"SAMPLE title {i}" for i in range(1, 6)],
    "thumbnail_concept": "Red LED close-up, clerk silhouette behind glass (SAMPLE)",
    "style_bible": {
        "visual_era_and_tone": "late 1990s office, cold, procedural dread",
        "color_grading_lut": "teal shadows, amber practicals, low saturation",
        "lens_and_grain_spec": "35mm, shallow depth of field, fine film grain",
        "negative_prompt": "text, watermark, logo, extra fingers, deformed hands, blurry",
        "entity_locks": [
            {"entity_token": "CHAR_CLERK_01", "locked_visual_description": CLERK,
             "reference_image_prompt": f"portrait of {CLERK}, neutral background, {STYLE}"},
            {"entity_token": "OBJ_PRINTER_01", "locked_visual_description": PRINTER,
             "reference_image_prompt": f"product shot of {PRINTER}, plain wall background, {STYLE}"},
            {"entity_token": "LOC_OFFICE_01", "locked_visual_description": OFFICE,
             "reference_image_prompt": f"wide establishing shot of {OFFICE}, {STYLE}"},
        ],
    },
    "acts": [
        {"act_number": n, "act_title": f"Act {n}", "narrative_phase": ph, "target_scene_count": c,
         "story_beats": ["beat 1", "beat 2", "beat 3"], "open_loop_cliffhanger": "SAMPLE cliffhanger"}
        for n, ph, c in [(1, "HOOK", 12), (2, "SETUP", 30), (3, "ESCALATION", 38),
                         (4, "CLIMAX", 32), (5, "RESOLUTION", 18)]
    ],
    "unresolved_hooks": [],
}

script = MasterScript.model_validate({
    "run_id": f"sample-{LANG}", "language": LANG, "source_rival_url": "https://youtube.com/watch?v=SAMPLE",
    "plan": plan, "scenes": scenes,
})
finalize_timing(script)

out = Path(__file__).resolve().parents[1] / "samples" / f"master_script.sample.{LANG}.json"
out.parent.mkdir(exist_ok=True)
out.write_text(script.model_dump_json(indent=2, exclude_none=False), encoding="utf-8")
print("wrote", out)
print(json.dumps(budget_report(script), indent=2, ensure_ascii=False))
