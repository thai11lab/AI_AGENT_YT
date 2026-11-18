"""CLI độc lập cho Agent 4 (Master Compositor & Final Cut)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_05_final_compositor.compositor_engine import compose_final_video  # noqa: E402
from shared.contracts import Phase2Manifest  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Chạy độc lập Agent 4: Master Compositor")
    parser.add_argument("package_dir", help="Đường dẫn tới thư mục production_package/<run_id>")
    parser.add_argument("--max-scenes", type=int, default=0)
    args = parser.parse_args()

    pkg = Path(args.package_dir).resolve()
    ms = json.loads((pkg / "master_script.json").read_text(encoding="utf-8"))
    out_root = pkg / "phase2_output"
    manifest = Phase2Manifest.model_validate_json((out_root / "phase2_manifest.json").read_text(encoding="utf-8"))

    scenes = ms["scenes"][: args.max_scenes] if args.max_scenes > 0 else ms["scenes"]
    final_mp4 = compose_final_video(
        scenes=scenes,
        voice_outputs=manifest.voice_outputs,
        motion_outputs=manifest.motion_outputs,
        work_dir=out_root,
        final_mp4_path=out_root / "final_documentary.mp4",
    )
    print(f"[Agent Compositor] Xuất xưởng video thành công -> {final_mp4}")


if __name__ == "__main__":
    main()
