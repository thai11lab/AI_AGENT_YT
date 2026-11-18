"""Unit Tests cho Agent 08: SQLiteFTS5MemoryBackend + Two-Pass Human Cadence Critic."""
import time
from pathlib import Path

from agents.agent_08_self_learner import (
    SQLiteFTS5MemoryBackend,
    analyze_scene_prosody,
    build_human_memory_prompt_block,
    evaluate_and_self_learn,
    infer_niche_tag,
    prune_and_optimize_memory_bank,
    score_human_cadence,
)


def test_sqlite_fts5_seed_and_fast_retrieval(tmp_path: Path):
    db_file = tmp_path / "test_script_brain.db"
    brain = SQLiteFTS5MemoryBackend(db_path=db_file)

    st = brain.stats()
    assert st["total_memories"] >= 10
    assert st["golden_patterns"] >= 10

    t0 = time.perf_counter()
    hits = brain.retrieve_context(
        niche="football",
        act_phase="HOOK",
        query_text="transfer fee contract flop dressing room",
        top_k=3,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert len(hits) == 3
    assert hits[0]["niche"] == "football"
    assert "Eighty-five million euros" in hits[0]["human_gold_text"]
    assert elapsed_ms < 25.0


def test_user_correction_priority_and_dedupe(tmp_path: Path):
    db_file = tmp_path / "test_user_fix.db"
    brain = SQLiteFTS5MemoryBackend(db_path=db_file)

    row_id = brain.record_user_correction(
        old_slide_text="The coach made a mistake in the second half.",
        user_new_text="Minute sixty-two. Look at that thirty-yard gap in midfield. That is a tactical suicide note.",
        niche="football",
        act_phase="CLIMAX",
    )
    assert row_id > 0

    hits = brain.retrieve_context(
        niche="football",
        act_phase="CLIMAX",
        query_text="midfield gap tactical mistake",
        top_k=2,
    )
    assert hits[0]["memory_type"] == "USER_FIX"
    assert hits[0]["win_score"] == 100.0


def test_learn_from_competitor_transcript_and_cadence_scoring(tmp_path: Path):
    db_file = tmp_path / "test_miner.db"
    brain = SQLiteFTS5MemoryBackend(db_path=db_file)

    fake_rival_transcript = (
        "When the medical board reviewed the file on Tuesday morning everything looked completely normal on paper. "
        "Except it was a lie. "
        "For fifteen years the hospital administrators buried every single anomalous brain scan inside a locked basement cabinet. "
        "Wait—why would anyone hide that? "
        "Because the moment you compare the timestamps the entire legal definition of death collapses."
    )
    learned = brain.learn_from_competitor_transcript(
        fake_rival_transcript,
        niche="general",
        source_title="Dying Is Complicated",
    )
    assert learned >= 1

    # So sánh điểm Human Score giữa văn phong "đọc slide" vs văn phong "con người có chính kiến"
    slide_vo = [
        "The documentary presents the official guidelines and shows internal memos.",
        "Furthermore, in the sterile chaos of the hospital, a chilling silence occurred.",
    ]
    human_vo = [
        "On paper, the patient was declared dead at midnight. In reality? The brain scanner strapped to his skull just erupted.",
        "Pause right there. Look at the timestamp on page fourteen—that makes zero sense.",
    ]

    slide_metrics = score_human_cadence(slide_vo)
    human_metrics = score_human_cadence(human_vo)

    assert human_metrics["human_score"] > slide_metrics["human_score"] + 2.5
    assert human_metrics["stance_hits"] >= 3
    assert slide_metrics["slide_penalties"] >= 2

    eval_res = evaluate_and_self_learn(human_vo, niche="general", act_phase="HOOK", brain=brain)
    assert eval_res["human_score"] >= 8.0

    prompt_block = build_human_memory_prompt_block(
        niche=infer_niche_tag("Premier League transfer fee manager"),
        act_phase="HOOK",
        query_text="transfer fee contract",
        brain=brain,
    )
    assert "TWO-PASS MENTAL PROCESS" in prompt_block
    assert "NEVER WRITE SLIDE-STYLE LIKE THIS" in prompt_block
    assert "WRITE HUMAN-STYLE LIKE THIS" in prompt_block


def test_prune_and_optimize_memory_bank(tmp_path: Path):
    db_file = tmp_path / "test_prune.db"
    brain = SQLiteFTS5MemoryBackend(db_path=db_file)

    # Giả lập 1 câu cụt ngủn bị lọt vào DB
    brain.add_memory(
        memory_type="GOLDEN",
        niche="general",
        act_phase="HOOK",
        human_gold_text="Quá ngắn.",
        win_score=10.0,
    )
    # Giả lập 1 câu do User sửa tay (không bao giờ bị xóa dù ngắn)
    brain.record_user_correction(
        old_slide_text="Câu cũ",
        user_new_text="Câu user sửa tay ngắn nhưng phải được bảo vệ tuyệt đối.",
        niche="general",
        act_phase="HOOK",
    )

    res = prune_and_optimize_memory_bank(brain=brain, max_entries_per_niche=50)
    assert res["pruned_entries"] >= 1
    assert res["user_fixes"] == 1


def test_vocal_prosody_breathing_and_intensity_curve():
    vo = (
        "Trên giấy tờ bệnh án, ranh giới giữa sự sống và cái chết chỉ là một đường kẻ thẳng tắp trên màn hình theo dõi nhịp tim. "
        "Nghe thì có vẻ rất rõ ràng và dứt khoát. "
        "Nhưng khi các nhà thần kinh học mở băng ghi dữ liệu não bộ sau thời điểm ngừng tim ba mươi giây, toàn bộ định nghĩa y khoa hàng trăm năm qua bỗng nhiên sụp đổ."
    )
    prosody = analyze_scene_prosody(vo, act_phase="HOOK", pause_after_sec=0.3)

    assert "—" in prosody["polished_vo"] or "..." in prosody["polished_vo"]
    assert len(prosody["segments"]) >= 3
    assert prosody["recommended_pause_after_sec"] >= 0.65
    intensities = {s["intensity"] for s in prosody["segments"]}
    assert "HIGH_SURGE" in intensities


