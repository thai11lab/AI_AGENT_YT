"""CLI độc lập cho Agent 3 (Hybrid Motion Engine)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_04_motion_broll.motion_engine import render_scene_motion  # noqa: E402
from shared.contracts import VisualSceneOutput  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Chạy độc lập Agent 3: Motion & 2.5D Parallax")
    parser.add_argument("package_dir", help="Đường dẫn tới thư mục production_package/<run_id>")
    parser.add_argument("--max-scenes", type=int, default=0)
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()

    pkg = Path(args.package_dir).resolve()
    ms = json.loads((pkg / "master_script.json").read_text(encoding="utf-8"))
    vis_dir = pkg / "phase2_output" / "visual"
    out_dir = pkg / "phase2_output" / "motion"

    scenes = ms["scenes"][: args.max_scenes] if args.max_scenes > 0 else ms["scenes"]
    for sc in scenes:
        sid = sc["scene_id"]
        vis = VisualSceneOutput(
            scene_id=sid,
            visual_mode=sc.get("visual_mode", "STATIC_PARALLAX"),
            base_image_path=str(vis_dir / f"{sid}.png"),
        )
        res = render_scene_motion(sc, vis, sc.get("duration_sec", 5.0), out_dir, force_local=args.local)
        print(f"[Agent Motion] {res.scene_id}: {res.motion_engine} ({res.duration_sec}s) -> {res.video_clip_path}")


if __name__ == "__main__":
    main()
