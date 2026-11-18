import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.schemas import MasterScript  # noqa: E402
from core.timing import finalize_timing  # noqa: E402
from core.render_plan import resolve_render_plan, summarize  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "master_script.sample.en.json"


def load():
    s = MasterScript.model_validate(json.loads(SAMPLE.read_text(encoding="utf-8")))
    return finalize_timing(s)


def test_local_only_has_no_video_and_same_script():
    s = load()
    plan = resolve_render_plan(s)                      # mặc định local_only
    assert "VIDEO_I2V" not in summarize(plan)
    assert all(t.fallback is None for t in plan)


def test_cloud_video_picks_top_priority_with_fallback():
    s = load()
    s.output_spec.max_premium_clips = 2
    plan = resolve_render_plan(s, "cloud_video")
    video = [t for t in plan if t.renderer == "VIDEO_I2V"]
    assert len(video) == 2
    assert all(t.fallback == "PARALLAX_2_5D" for t in video)
    assert [t.scene_id for t in video] == ["S001", "S002"]     # priority 5 rồi 4
    assert len(plan) == len(s.scenes)                           # không mất cảnh nào


def test_zero_premium_budget_equals_local():
    s = load()
    s.output_spec.max_premium_clips = 0
    assert "VIDEO_I2V" not in summarize(resolve_render_plan(s, "cloud_video"))

