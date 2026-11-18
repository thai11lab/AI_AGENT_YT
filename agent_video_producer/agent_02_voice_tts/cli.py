"""CLI độc lập cho Agent 1 (Emotional Voice & Voice Cloning)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_02_voice_tts.voice_engine import synthesize_scene_voice  # noqa: E402
from shared.channels import get_channel_persona  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Chạy độc lập Agent 1: Emotional Voice Studio")
    parser.add_argument("package_dir", help="Đường dẫn tới thư mục production_package/<run_id>")
    parser.add_argument("--channel", default="med_forensic_us", help="Mã kênh trong shared/channels.py")
    parser.add_argument("--voice-sample", default="", help="URL hoặc đường dẫn mẫu giọng (5-10s) để clone")
    parser.add_argument("--max-scenes", type=int, default=0, help="Giới hạn số cảnh để chạy thử")
    parser.add_argument("--local", action="store_true", help="Ép chạy hoàn toàn miễn phí trên máy")
    args = parser.parse_args()

    pkg = Path(args.package_dir).resolve()
    ms = json.loads((pkg / "master_script.json").read_text(encoding="utf-8"))
    persona = get_channel_persona(args.channel, ms.get("language", "en"))
    if args.voice_sample:
        persona.voice_sample_path = args.voice_sample

    out_dir = pkg / "phase2_output" / "voice"
    scenes = ms["scenes"][: args.max_scenes] if args.max_scenes > 0 else ms["scenes"]
    for sc in scenes:
        res = synthesize_scene_voice(sc, out_dir, persona, force_local=args.local)
        print(f"[Agent Voice] {res.scene_id}: {res.duration_sec}s ({res.engine_used}) -> {res.audio_path}")


if __name__ == "__main__":
    main()
