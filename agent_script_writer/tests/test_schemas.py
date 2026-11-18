import copy
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import MasterScript  # noqa: E402
from core.timing import finalize_timing, budget_report  # noqa: E402

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def load(lang):
    return json.loads((SAMPLES / f"master_script.sample.{lang}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("lang", ["en", "vi"])
def test_sample_is_valid(lang):
    s = MasterScript.model_validate(load(lang))
    finalize_timing(s)
    rep = budget_report(s)
    assert rep["hook_ai_share"] == 1.0 and not rep["scenes_over_clip_limit"]


def bad(mutator, lang="en"):
    d = copy.deepcopy(load(lang))
    mutator(d)
    with pytest.raises(ValidationError):
        MasterScript.model_validate(d)


def test_digit_in_voiceover():
    bad(lambda d: d["scenes"][0].update(voiceover_text="At 11:47 the printer jammed. Nobody looked up."))


def test_banned_phrase():
    bad(lambda d: d["scenes"][1].update(
        voiceover_text="Without further ado the clerk kept typing, as if the room were safe."))


def test_trigger_not_in_voiceover():
    bad(lambda d: d["scenes"][0]["audio_cues"][0].update(trigger_word="explosion"))


def test_hook_must_be_ai_video():
    bad(lambda d: d["scenes"][0].update(visual_mode="STATIC_PARALLAX"))


def test_parallax_requires_layers():
    bad(lambda d: d["scenes"][3].update(parallax_spec=None))


def test_document_requires_asset():
    bad(lambda d: d["scenes"][4].update(document_asset=None))


def test_unknown_entity():
    bad(lambda d: d["scenes"][0].update(reference_entities=["CHAR_GHOST_99"]))


def test_duplicate_scene_id():
    bad(lambda d: d["scenes"][1].update(scene_id="S001"))


def test_short_flux_prompt():
    bad(lambda d: d["scenes"][0].update(flux_base_image_prompt="too short"))


def test_vietnamese_digit_rejected():
    bad(lambda d: d["scenes"][0].update(
        voiceover_text="11 giờ bốn mươi bảy, máy in kẹt giấy. Không ai ngẩng lên."), lang="vi")


def test_ai_video_requires_fallback_parallax():
    bad(lambda d: d["scenes"][0].update(parallax_spec=None))


def test_normalize_all_scenes_heals_duplicates_and_digits():
    from core.orchestrator import normalize_all_scenes
    from core.schemas import ActScenes, MasterPlan

    d = load("en")
    plan = MasterPlan.model_validate(d["plan"])
    raw_batch = {
        "scenes": [
            {
                "scene_id": "S001",
                "act_number": 1,
                "narrative_phase": "HOOK",
                "visual_mode": "STATIC_PARALLAX",
                "voiceover_text": "In 20 minutes the cold monitor stopped delves into silence.",
                "flux_base_image_prompt": "short prompt",
                "reference_entities": ["CHAR_GHOST_NOT_IN_BIBLE"],
                "audio_cues": [{"sfx_category": "WHOOSH", "trigger_word": "missingword", "volume_db": -6.0}],
            },
            {
                "scene_id": "S001",
                "act_number": 1,
                "narrative_phase": "HOOK",
                "visual_mode": "DOCUMENT_HIGHLIGHT",
                "voiceover_text": "After 24 hours the lab door stayed locked in the dark.",
                "flux_base_image_prompt": "another short prompt",
                "reference_entities": ["UNKNOWN_ENTITY"],
                "audio_cues": [{"sfx_category": "IMPACT", "trigger_word": "nonexistent", "volume_db": -6.0}],
            },
        ]
    }
    parsed = ActScenes.model_validate(raw_batch)
    healed = normalize_all_scenes(parsed.scenes, plan, "en")
    ms = MasterScript(
        run_id="run-test-heal",
        language="en",
        source_rival_url="https://youtube.com/watch?v=test",
        plan=plan,
        scenes=healed,
    )
    assert [s.scene_id for s in ms.scenes] == ["S001", "S002"]
    assert all(not s.reference_entities for s in ms.scenes)

