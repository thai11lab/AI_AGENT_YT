"""1-CLICK NICHE RADAR & FULL AI AGENT ORCHESTRATOR (Phase 1 + Phase 2).
Chỉ cần chạy file này, bấm chọn số thứ tự ngách (1-4), hệ thống tự động:
1. Quét video nổ view đột biến (Outlier) trong ngách ít đối thủ đó.
2. Lên Plan phân công cho 9 AI Agents (Phase 1 Research/Script + Phase 2 Voice/Visual/Motion/Compositor).
3. Chạy tự động từ A-Z ra thẳng file video .mp4 hoàn chỉnh.
"""
import argparse
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "agent_script_writer"))
sys.path.insert(0, str(WORKSPACE / "agent_video_producer"))

from agent_video_producer.run_phase2 import run_phase2_pipeline  # noqa: E402
from core.orchestrator import run_autonomous_brain  # noqa: E402
from tools.niche_radar import scan_breakout_niches  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="1-Click Niche Radar & Auto-Production")
    parser.add_argument("--url", default="", help="Chạy thẳng từ URL YouTube cụ thể (bỏ qua bước quét 20 ngách)")
    parser.add_argument("--channel", default="", help="Preset kênh (VD: gta_mystery, ch01_med_forensic, ch20_dieu_tra_vn)")
    parser.add_argument("--pick", type=int, default=0, help="Chọn thẳng ngách số 1..20 (nếu để 0 sẽ hỏi trên màn hình)")
    parser.add_argument("--max-scenes", type=int, default=5, help="Số cảnh dựng video (mặc định 5 cảnh đầu để xem nhanh, để 0 là dựng hết 128 cảnh)")
    parser.add_argument("--lang", choices=["en", "vi"], default="en")
    args = parser.parse_args()

    if args.url.strip():
        target_url = args.url.strip()
        channel_id = args.channel.strip() or ("ch20_dieu_tra_vn" if args.lang == "vi" else "ch01_med_forensic")
        print(f"\n🚀 CHẠY THẲNG TỪ URL: {target_url} | Kênh: {channel_id} | Ngôn ngữ: {args.lang.upper()}")
    else:
        print("\n" + "=" * 72)
        print("🔥 ĐANG QUÉT CÁC NGÁCH NỔ VIEW ĐỘT BIẾN & ÍT ĐỐI THỦ (NICHE RADAR)...")
        print("=" * 72)
        niches = scan_breakout_niches(live_youtube_scan=True)

        for idx, n in enumerate(niches, 1):
            vid = n["selected_video"]
            print(f"\n[{idx}] 🎯 {n['niche_name']}")
            print(f"    • RPM: {n['rpm_range']} | Cạnh tranh: {n['competition_level']} | Điểm Outlier: {vid['outlier_score']}")
            print(f"    • Video mồi phát hiện: {vid['title']} ({vid['views']:,} views)")
            print(f"    • URL: {vid['url']}")
            print(f"    • Plan 5 AI Agents: {' -> '.join(s.split(':')[0] for s in n['agent_execution_plan'])}")

        choice = args.pick
        if choice < 1 or choice > len(niches):
            raw = input(f"\n👉 Nhập số thứ tự ngách bạn muốn làm [1-{len(niches)}] (nhấn Enter để chọn [1]): ").strip()
            choice = int(raw) if raw.isdigit() and 1 <= int(raw) <= len(niches) else 1

        picked = niches[choice - 1]
        vid = picked["selected_video"]
        target_url = vid["url"]
        channel_id = args.channel.strip() or picked["channel_preset"]

        print("\n" + "=" * 72)
        print(f"🚀 ĐÃ CHỐT NGÁCH [{choice}]: {picked['niche_name']}")
        print("📋 KẾ HOẠCH ĐIỀU PHỐI DÀN AI AGENT:")
        for step in picked["agent_execution_plan"]:
            print(f"   ✓ {step}")
        print("=" * 72)

    # Bước 1: Chạy Phase 1 (có Checkpoint tự động)
    pkg_dir = run_autonomous_brain(
        youtube_url=target_url,
        language=args.lang,
        auto_approve_gate=True,
    )

    # Bước 2: Chạy Phase 2 (4 AI Agents dựng video .mp4)
    final_mp4 = run_phase2_pipeline(
        package_dir=pkg_dir,
        channel_id=channel_id,
        max_scenes=args.max_scenes,
    )
    print(f"\n🎉 XONG TOÀN BỘ! Mở xem video tại: {final_mp4}")


if __name__ == "__main__":
    main()
