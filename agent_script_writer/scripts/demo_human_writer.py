"""Script Demo & A/B Benchmark chất lượng Agent Script Writer (Trước vs Sau khi có SQLite FTS5 + Two-Pass Human Cadence).
Chỉ test 8 cảnh đầu tiên của Hồi 1 (HOOK - 60 giây đầu) để bạn thấy rõ kết quả trong ~15 giây mà không cần đợi chạy cả 128 cảnh!
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.agent_08_self_learner import (  # noqa: E402
    SQLiteFTS5MemoryBackend,
    analyze_scene_prosody,
    evaluate_and_self_learn,
    infer_niche_tag,
    score_human_cadence,
)
from core.orchestrator import write_act_scenes_with_healing  # noqa: E402
from core.schemas import ActBlueprint, EvidenceItem, MasterPlan  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Demo A/B chất lượng Agent Script Writer (8 cảnh Hook + Phổ Hơi Thở & Cường Độ Giọng)")
    parser.add_argument("--lang", default="vi", choices=["en", "vi"], help="Ngôn ngữ demo (en hoặc vi)")
    parser.add_argument("--country", default="", help="Mã quốc gia tách giọng Nam trầm (US | UK | AU | CA | VN_BAC | VN_NAM | JP | FR | ES)")
    parser.add_argument("--engine", default="auto", choices=["auto", "kokoro", "omnivoice", "vieneu", "edge"], help="Chọn Engine TTS để test")
    parser.add_argument("--voice-style", default="", help="Đổi chất giọng OmniVoice (deep_baritone | young_sharp | whisper_thriller | news_anchor | hoặc nhập mô tả tiếng Anh tùy ý)")
    parser.add_argument("--ref-audio", default="", help="Đường dẫn file .wav/.mp3 (5-10s) để OmniVoice Zero-Shot Clone đúng giọng người thật đó")
    parser.add_argument("--compare-tts", action="store_true", help="Chạy A/B Benchmark so sánh trực tiếp Kokoro-82M vs OmniVoice trên các quốc gia")
    parser.add_argument("--scenes", type=int, default=6, help="Số cảnh muốn viết thử (mặc định: 6 cảnh)")
    parser.add_argument("--instant", action="store_true", help="Demo tức thì (< 0.1s, không cần gọi API) từ kho mẫu Golden SQLite FTS5")
    parser.add_argument("--speak", action="store_true", help="Xuất luôn file âm thanh giọng đọc .wav có ngắt nghỉ hơi thở & EQ lên xuống cho cảnh đầu tiên")
    args = parser.parse_args()

    ckpt_path = ROOT / ".cache" / "checkpoints" / "ckpt_fEjvSbI_PT4_en.json"
    if not ckpt_path.exists():
        print(f"Không tìm thấy checkpoint {ckpt_path}. Hãy chạy run_pipeline.py trước.")
        return

    ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
    vault = [EvidenceItem.model_validate(e) for e in ckpt["debate"]["vault"]]
    master_plan = MasterPlan.model_validate(ckpt["master_plan"])

    # 1. Lấy 8 cảnh cũ (trước khi nâng cấp hoặc từ bản chạy trước) để so sánh A/B
    old_pkg_script = ROOT / "production_package" / "run-en-20261117-002829" / "master_script.json"
    old_vos = []
    if old_pkg_script.exists():
        old_data = json.loads(old_pkg_script.read_text(encoding="utf-8"))
        old_vos = [s["voiceover_text"] for s in old_data.get("scenes", [])[: args.scenes]]

    brain = SQLiteFTS5MemoryBackend()
    print("\n" + "=" * 80)
    print(f"🧠 DEMO TEST CHẤT LƯỢNG AGENT SCRIPT WRITER (SQLite FTS5 + Two-Pass Human Voice)")
    print(f"   DB Memory: {brain.db_path} | Stats: {brain.stats()}")
    print("=" * 80)

    if old_vos:
        old_score = score_human_cadence(old_vos)
        print(f"\n📊 [BẢN CŨ TRƯỚC KHI NÂNG CẤP] ({len(old_vos)} cảnh đầu):")
        print(
            f"   Human Score: {old_score['human_score']}/10 | "
            f"Burstiness (σ): {old_score['burstiness']} | "
            f"Stance Markers: {old_score['stance_hits']} | "
            f"Lỗi đọc Slide: {old_score['slide_penalties']}"
        )
        for i, vo in enumerate(old_vos[:4], 1):
            print(f"   [Cũ S{i:03d}] {vo}")

    # 1b. Chế độ A/B Benchmark so sánh trực tiếp Kokoro-82M vs OmniVoice & Danh mục Giọng Nam Các Nước
    if args.compare_tts:
        sys.path.insert(0, str(ROOT.parent / "agent_video_producer"))
        from shared.channels import COUNTRY_VOICE_PACKS, get_channel_persona
        from agent_02_voice_tts.voice_engine import synthesize_scene_voice

        print("\n🌍 [DANH MỤC GIỌNG NAM TRẦM ĐA QUỐC GIA (COUNTRY VOICE PACKS)]:")
        for c_code, pack in COUNTRY_VOICE_PACKS.items():
            print(
                f"   • [{c_code}] {pack['name']}\n"
                f"       ├─ Kokoro-82M : voice='{pack['kokoro_voice']}' (lang_code='{pack['kokoro_lang_code']}')\n"
                f"       ├─ OmniVoice  : lang='{pack['omnivoice_lang']}' | style='{pack['omnivoice_style_prompt'][:65]}...'\n"
                f"       └─ Edge Neural: voice='{pack['edge_voice']}'"
            )

        print("\n" + "=" * 80)
        print("⚖️ BẢNG SO SÁNH KỸ THUẬT: KOKORO-82M vs OMNIVOICE (k2-fsa)")
        print("=" * 80)
        print("1. 🇺🇸🇬🇧🇦🇺🇨🇦 Tiếng Anh (Mỹ, Anh, Úc, Canada) & 🇯🇵🇫🇷🇪🇸 (Nhật, Pháp, TBN):")
        print("   👉 KOKORO-82M THẮNG TUYỆT ĐỐI về độ tự nhiên của nhịp thở (Prosody), tốc độ siêu nhẹ (82M params, chạy ~0.2s/câu trên Mac M4, tốn < 400MB RAM).")
        print("   👉 Mã giọng Nam khuyên dùng: Mỹ ('am_adam', 'am_fenrir'), Anh Quốc ('bm_george', 'bm_daniel'), Úc ('bm_lewis'), Canada ('am_liam').")
        print("\n2. 🇻🇳 Tiếng Việt & Clone Giọng Mẫu Bất Kỳ (600+ Ngôn Ngữ):")
        print("   👉 OMNIVOICE THẮNG TUYỆT ĐỐI vì Kokoro-82M KHÔNG hỗ trợ âm vị Tiếng Việt ('vi').")
        print("   👉 OmniVoice hỗ trợ native Tiếng Việt + Zero-Shot Voice Cloning (chỉ cần đưa 1 đoạn wav 5-10s giọng Nam trầm bạn thích vào `voice_sample_path` là nó nhại lại 100% âm sắc đó).")
        print("=" * 80)

        if args.speak:
            import subprocess

            c_target = (args.country or ("VN" if args.lang == "vi" else "US")).upper()
            sample_text = (
                "Đúng hai giờ mười bốn phút sáng tại phòng hồi sức Vancouver, tim bệnh nhân đã ngừng đập hoàn toàn. Thế nhưng chiếc máy đo điện não trên đầu ông ấy... lại vừa ghi nhận một cơn bão sóng gamma."
                if c_target == "VN"
                else "In February two thousand sixteen, an eighty-seven-year-old patient in Vancouver flatlined. Doctors called the time of death. — Except someone forgot to turn off the brain scanner strapped to his skull... and thirty seconds later, it erupted."
            )
            out_voice_dir = ROOT / ".cache" / "demo_prosody_audio"
            for eng in ("kokoro", "omnivoice"):
                persona = get_channel_persona("ch01_med_forensic", lang=args.lang, country=c_target)
                fake_sc = {"scene_id": f"AB_{c_target}_{eng.upper()}", "voiceover_text": sample_text, "audio_cues": []}
                t_start = time.time()
                v_res = synthesize_scene_voice(fake_sc, out_dir=out_voice_dir, persona=persona, preferred_engine=eng)
                dt = round(time.time() - t_start, 2)
                print(f"\n🔊 [{eng.upper()} | Quốc gia: {c_target}] Hoàn tất trong {dt}s -> Engine thực tế: {v_res.engine_used}")
                print(f"   File: {v_res.audio_path} ({v_res.duration_sec}s)")
                subprocess.run(["afplay", v_res.audio_path], check=False)
        return

    # 2. Nếu chọn --instant, lấy trực tiếp các mẫu câu chuẩn trong SQLite FTS5 để demo tức thì (< 0.1s)
    if args.instant:
        hits = brain.retrieve_context(
            niche="general",
            act_phase="HOOK",
            query_text="hồ sơ bệnh viện sóng não gamma" if args.lang == "vi" else "hospital flatline brain scanner eeg",
            top_k=4,
        )
        print(f"\n⚡ [CHẾ ĐỘ DEMO TỨC THÌ — PHỔ HƠI THỞ & ĐƯỜNG CONG CƯỜNG ĐỘ GIỌNG ({args.lang.upper()})]:")
        chosen_sample_vo = ""
        for idx, h in enumerate(hits, 1):
            vo_sample = h["human_gold_text"]
            if not chosen_sample_vo and (
                (args.lang == "en" and "February" in vo_sample) or (args.lang == "vi" and "Vancouver" in vo_sample)
            ):
                chosen_sample_vo = vo_sample
            p_info = analyze_scene_prosody(vo_sample, act_phase=h["act_phase"], pause_after_sec=0.4)
            print(f"\n🎬 [Mẫu S{idx:03d}] (Ngách: {h['niche'].upper()} | Hồi: {h['act_phase']} | 🫁 Nghỉ cuối cảnh: {p_info['recommended_pause_after_sec']}s)")
            if h.get("bad_slide_text"):
                print(f"   ❌ Bản Đọc Slide : \"{h['bad_slide_text']}\"")
            print(f"   🎙️ Bản Người Thật: \"{p_info['polished_vo']}\"")
            print(f"   📈 Đường Cong Lực: {p_info['intensity_arc']}")
            print(f"   🫁 Phổ Ngắt Nghỉ :\n      {p_info['annotated_performance_script']}")

        if args.speak:
            import subprocess
            sys.path.insert(0, str(ROOT.parent / "agent_video_producer"))
            from agent_02_voice_tts.voice_engine import synthesize_scene_voice
            from shared.channels import get_channel_persona

            vo_to_read = chosen_sample_vo or hits[0]["human_gold_text"]
            c_target = (args.country or ("VN" if args.lang == "vi" else "US")).upper()
            preset_id = "ch20_dieu_tra_vn" if c_target.startswith("VN") else "ch01_med_forensic"
            persona = get_channel_persona(preset_id, lang=args.lang, country=c_target)

            style_presets = {
                "deep_baritone": "male, middle-aged, very low pitch",
                "young_sharp": "male, young adult, moderate pitch",
                "whisper_thriller": "male, middle-aged, low pitch, whisper",
                "news_anchor": "male, elderly, low pitch",
            }
            style_tag = "default"
            if args.voice_style.strip():
                vs = args.voice_style.strip()
                style_tag = vs if vs in style_presets else "custom"
                persona.omnivoice_style_prompt = style_presets.get(vs, vs)
            if args.ref_audio.strip():
                persona.voice_sample_path = args.ref_audio.strip()
                style_tag = "cloned"

            out_voice_dir = ROOT / ".cache" / "demo_prosody_audio"
            fake_scene = {"scene_id": f"DEMO_{c_target}_{args.engine.upper()}_{style_tag}", "voiceover_text": vo_to_read, "audio_cues": []}
            v_out = synthesize_scene_voice(fake_scene, out_dir=out_voice_dir, persona=persona, preferred_engine=args.engine)
            print(f"\n🔊 [Quốc gia: {c_target}] Đã xuất file âm thanh tại: {v_out.audio_path} (Engine: {v_out.engine_used} | Dài: {v_out.duration_sec}s)")
            if v_out.engine_used == "local_studio_synth":
                print("⚠️ Cảnh báo: Không kết nối được Edge-TTS / OmniVoice nên file vừa tạo chỉ là sóng âm test offline (không phải giọng nói). Hãy kiểm tra mạng hoặc cài `omnivoice`!")
            else:
                print("▶️ Đang phát âm thanh ra loa Mac của bạn (`afplay`)...")
                subprocess.run(["afplay", v_out.audio_path], check=False)
        return

    # 3. Tạo bản sao Hồi 1 giới hạn đúng args.scenes cảnh để chạy LIVE nhanh (~15s)
    act1: ActBlueprint = master_plan.acts[0].model_copy(deep=True)
    act1.target_scene_count = args.scenes

    print(f"\n🚀 Đang gọi LLM viết LIVE {args.scenes} cảnh Hồi 1 (Ngôn ngữ: {args.lang.upper()}) với ký ức SQLite FTS5...")
    t0 = time.time()
    new_scenes, _ = write_act_scenes_with_healing(
        act=act1,
        plan=master_plan,
        vault=vault,
        language=args.lang,
        start_scene_num=1,
        prev_bridge="COLD OPEN inside a real documented ICU or neurological lab at the exact second the EEG brain monitor spikes after cardiac flatline.",
    )
    elapsed = round(time.time() - t0, 1)

    new_vos = [s.voiceover_text for s in new_scenes]
    niche_tag = infer_niche_tag(act1.act_title + " " + " ".join(new_vos))
    new_score = evaluate_and_self_learn(new_vos, niche=niche_tag, act_phase="HOOK", brain=brain)

    print("\n" + "=" * 80)
    print(f"✅ KẾT QUẢ BẢN MỚI (Hoàn thành trong {elapsed}s — Đã tự học thêm vào SQLite FTS5):")
    print(
        f"   Human Score: {new_score['human_score']}/10 | "
        f"Burstiness (σ): {new_score['burstiness']} | "
        f"Stance Markers: {new_score['stance_hits']} | "
        f"Lỗi đọc Slide: {new_score['slide_penalties']}"
    )
    print("=" * 80)
    for sc in new_scenes:
        ost = f" | 🖥️ On-Screen: [{sc.on_screen_text}]" if sc.on_screen_text else ""
        sfx = ", ".join(f"{c.sfx_category}@'{c.trigger_word}'" for c in sc.audio_cues)
        prosody = analyze_scene_prosody(sc.voiceover_text, act_phase=sc.narrative_phase, pause_after_sec=sc.pause_after_sec)
        print(f"\n🎬 [{sc.scene_id}] ({sc.visual_mode}{ost}) | 🫁 Nghỉ cuối cảnh: {sc.pause_after_sec}s")
        print(f"   🎙️ VO Gốc        : \"{sc.voiceover_text}\"")
        print(f"   📈 Cường độ Giọng: {prosody['intensity_arc']}")
        print(f"   🫁 Phổ Hơi Thở   :\n      {prosody['annotated_performance_script']}")
        print(f"   🔊 Điểm Nổ SFX   : {sfx}")

    print("\n" + "=" * 80)
    print(f"📈 Trạng thái Bộ nhớ SQLite FTS5 sau khi chạy: {brain.stats()}")
    print("=" * 80 + "\n")

    if args.speak and new_scenes:
        import subprocess
        sys.path.insert(0, str(ROOT.parent / "agent_video_producer"))
        from agent_02_voice_tts.voice_engine import synthesize_scene_voice
        from shared.channels import get_channel_persona

        preset_id = "ch20_dieu_tra_vn" if args.lang == "vi" else "ch01_med_forensic"
        persona = get_channel_persona(preset_id)
        out_voice_dir = ROOT / ".cache" / "demo_prosody_audio"
        sc0 = new_scenes[0].model_dump()
        v_out = synthesize_scene_voice(sc0, out_dir=out_voice_dir, persona=persona)
        print(f"🔊 Đã kết xuất file âm thanh giọng đọc có ngắt nghỉ hơi thở & EQ cường độ tại:\n   👉 {v_out.audio_path} (Engine: {v_out.engine_used} | Dài: {v_out.duration_sec}s)")
        print("▶️ Đang phát âm thanh ra loa Mac của bạn (`afplay`)...")
        subprocess.run(["afplay", v_out.audio_path], check=False)



if __name__ == "__main__":
    main()
