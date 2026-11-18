"""Chạy toàn bộ pipeline Giai đoạn 1 (Autonomous Brain v3.1).
Sử dụng:
    python scripts/run_pipeline.py "<youtube_url>" [--transcript path/to/transcript.txt] [--lang en|vi] [--interactive]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.orchestrator import run_autonomous_brain  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Chạy Autonomous Brain v3.1 Giai đoạn 1")
    parser.add_argument("url", help="URL video YouTube của đối thủ")
    parser.add_argument("--transcript", "-t", default=None, help="Đường dẫn file transcript dán tay (bỏ qua bóc băng)")
    parser.add_argument("--lang", "-l", choices=["en", "vi"], default="en", help="Ngôn ngữ kịch bản đầu ra ('en' hoặc 'vi')")
    parser.add_argument("--interactive", action="store_true", help="Dừng lại hỏi người dùng ở Human Gate trước khi viết kịch bản")
    parser.add_argument("--fresh", action="store_true", help="Xóa checkpoint cũ của video này và chạy lại từ đầu")
    parser.add_argument("--rewrite-acts", action="store_true", help="Giữ nguyên Research & MasterPlan từ checkpoint ($0), chỉ viết lại các cảnh (Node 6B)")

    args = parser.parse_args()

    out_path = run_autonomous_brain(
        youtube_url=args.url,
        manual_transcript_path=args.transcript,
        language=args.lang,
        auto_approve_gate=not args.interactive,
        fresh=args.fresh,
        rewrite_acts=args.rewrite_acts,
    )
    print(f"Hoàn tất. Kiểm tra thư mục: {out_path}")


if __name__ == "__main__":
    main()

