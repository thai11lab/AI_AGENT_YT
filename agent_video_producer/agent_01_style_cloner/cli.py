"""CLI độc lập cho Agent 0 (YouTube Channel Style Cloner)."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_01_style_cloner.style_cloner import clone_youtube_style  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Bóc tách và sao chép DNA dựng phim từ 1 kênh/video YouTube mẫu")
    parser.add_argument("youtube_url", help="URL kênh YouTube (ví dụ https://www.youtube.com/@fern-tv) hoặc URL video")
    parser.add_argument("--name", default=None, help="Đặt tên hồ sơ style (ví dụ: fern_style)")
    args = parser.parse_args()

    persona = clone_youtube_style(args.youtube_url, style_name=args.name)
    print("=" * 65)
    print(f"[STYLE CLONER] Đã sao chép thành công DNA của kênh: {persona.niche}")
    print("=" * 65)
    print(persona.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
