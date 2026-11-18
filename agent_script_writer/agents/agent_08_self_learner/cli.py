"""CLI độc lập cho Agent 08 (Self-Learner, Daily Curriculum Trainer & SQLite FTS5 Memory Bank)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agents.agent_08_self_learner import (  # noqa: E402
    SQLiteFTS5MemoryBackend,
    prune_and_optimize_memory_bank,
    run_daily_self_learning_cycle,
)


def main():
    parser = argparse.ArgumentParser(description="Quản lý & Huấn luyện Hàng ngày Bộ nhớ SQLite FTS5 (script_brain.db)")
    parser.add_argument("--learn-url", default="", help="Đưa URL video YouTube triệu view vào để Agent dùng LLM chưng cất mẫu câu song ngữ EN/VI nạp vào DB")
    parser.add_argument("--daily-scan", action="store_true", help="Tự động quét các video triệu view mới nổ qua Niche Radar để học văn phong hàng ngày")
    parser.add_argument("--max-videos", type=int, default=2, help="Số video tối đa cần học trong 1 chu kỳ --daily-scan")
    parser.add_argument("--prune", action="store_true", help="Dọn dẹp các mẫu câu ngắn/điểm thấp và tối ưu chỉ mục SQLite FTS5")
    parser.add_argument("--niche", default="auto", help="Nhãn ngách (football | netflix | gta | general)")
    parser.add_argument("--phase", default="HOOK", help="Hồi cần truy vấn thử (HOOK | SETUP | ESCALATION | CLIMAX | RESOLUTION)")
    parser.add_argument("--query", default="", help="Từ khóa ngữ cảnh để test tốc độ truy xuất BM25")
    args = parser.parse_args()

    brain = SQLiteFTS5MemoryBackend()

    if args.prune:
        p_res = prune_and_optimize_memory_bank(brain=brain)
        print(f"[Self-Learner] Đã tối ưu & cắt tỉa bộ nhớ: {json.dumps(p_res)}")

    if args.learn_url.strip():
        print(f"[Daily Trainer] Đang bóc băng & dùng LLM chưng cất tinh hoa văn phong từ {args.learn_url} (Song ngữ VI + EN)...")
        res = run_daily_self_learning_cycle(
            niche="all" if args.niche == "auto" else args.niche,
            languages=["vi", "en"],
            max_videos=1,
            custom_urls=[args.learn_url.strip()],
            use_llm_distiller=True,
            brain=brain,
        )
        print(f"[Daily Trainer] Kết quả chu kỳ học tập: Đã nạp thêm {res['new_patterns_learned']} mẫu câu tinh hoa mới!")

    elif args.daily_scan:
        print(f"[Daily Trainer] Đang kích hoạt Radar quét {args.max_videos} video triệu view mới nổ để tự học hàng ngày...")
        res = run_daily_self_learning_cycle(
            niche="all" if args.niche == "auto" else args.niche,
            languages=["vi", "en"],
            max_videos=args.max_videos,
            use_llm_distiller=True,
            brain=brain,
        )
        print(f"[Daily Trainer] Hoàn tất chu kỳ tự học hàng ngày: {json.dumps(res, ensure_ascii=False, indent=2)}")

    st = brain.stats()
    print("=" * 70)
    print(f"📊 THỐNG KÊ KHO TRI THỨC SQLITE FTS5 ({brain.db_path.name}): {json.dumps(st)}")
    print("=" * 70)
    q_niche = "general" if args.niche == "auto" else args.niche
    hits = brain.retrieve_context(niche=q_niche, act_phase=args.phase, query_text=args.query, top_k=4)
    for idx, h in enumerate(hits, 1):
        print(f"[{idx}] ({h['niche'].upper()} // {h['act_phase']} // WinScore={h['win_score']}):")
        if h.get("bad_slide_text"):
            print(f"    ❌ Slide : {h['bad_slide_text']}")
        print(f"    ✅ Human : {h['human_gold_text']}")
        print(f"    💡 Rule  : {h['why_it_works']}\n")


if __name__ == "__main__":
    main()
