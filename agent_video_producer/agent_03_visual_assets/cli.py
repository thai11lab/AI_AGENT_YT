"""CLI độc lập cho Agent 2 (Visual Studio Agent)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_03_visual_assets.visual_engine import generate_scene_visual  # noqa: E402
from shared.channels import get_channel_persona  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Chạy độc lập Agent 2: Visual Studio")
    parser.add_argument("package_dir", help="Đường dẫn tới thư mục production_package/<run_id>")
    parser.add_argument("--channel", default="med_forensic_us")
    parser.add_argument("--max-scenes", type=int, default=0)
    parser.add_argument("--local", action="store_true")
    args = parser.parse_args()

    pkg = Path(args.package_dir).resolve()
    ms = json.loads((pkg / "master_script.json").read_text(encoding="utf-8"))
    ev_list = json.loads((pkg / "evidence_dossier.json").read_text(encoding="utf-8"))
    ev_map = {e["evidence_id"]: e for e in ev_list if isinstance(e, dict) and "evidence_id" in e}
    persona = get_channel_persona(args.channel, ms.get("language", "en"))

    out_dir = pkg / "phase2_output" / "visual"
    scenes = ms["scenes"][: args.max_scenes] if args.max_scenes > 0 else ms["scenes"]
    for sc in scenes:
        res = generate_scene_visual(sc, out_dir, persona, evidence_map=ev_map, force_local=args.local)
        print(f"[Agent Visual] {res.scene_id} ({res.visual_mode}): {res.provider_used} -> {res.base_image_path}")


if __name__ == "__main__":
    main()
