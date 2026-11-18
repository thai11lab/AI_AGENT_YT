"""Bộ điều phối Giai đoạn 2 (Phase 2 Master Orchestrator).
Điều phối 4 AI Agent độc lập (agent_voice -> agent_visual -> agent_motion -> agent_compositor)
kèm cơ chế Checkpoint từng cảnh (lỗi ở cảnh nào chạy lại đúng từ cảnh đó, tốn $0 cho các cảnh đã xong).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agent_01_style_cloner.style_cloner import clone_youtube_style  # noqa: E402
from agent_02_voice_tts.voice_engine import synthesize_scene_voice  # noqa: E402
from agent_03_visual_assets.visual_engine import generate_scene_visual  # noqa: E402
from agent_04_motion_broll.motion_engine import render_scene_motion  # noqa: E402
from agent_05_final_compositor.compositor_engine import compose_final_video  # noqa: E402
from agent_06_qa_inspector.qa_inspector import (  # noqa: E402
    audit_final_video,
    deduplicate_and_audit_scenes,
)
from shared.channels import CHANNEL_PRESETS, get_channel_persona  # noqa: E402
from shared.contracts import Phase2Manifest  # noqa: E402


def _save_manifest(path: Path, manifest: Phase2Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)


def run_phase2_pipeline(
    package_dir: Path,
    channel_id: str = "med_forensic_us",
    voice_sample: str = "",
    max_scenes: int = 0,
    force_local: bool = False,
    fresh: bool = False,
    clone_style_url: str = "",
) -> Path:
    pkg = package_dir.resolve()
    ms_path = pkg / "master_script.json"
    ev_path = pkg / "evidence_dossier.json"
    if not ms_path.exists():
        raise FileNotFoundError(f"Không tìm thấy {ms_path}")

    ms = json.loads(ms_path.read_text(encoding="utf-8"))
    ev_list = json.loads(ev_path.read_text(encoding="utf-8")) if ev_path.exists() else []
    ev_map = {e["evidence_id"]: e for e in ev_list if isinstance(e, dict) and "evidence_id" in e}

    if clone_style_url.strip():
        print(f"[STYLE CLONER] Đang phân tích & sao chép DNA dựng phim từ: {clone_style_url}...", flush=True)
        persona = clone_youtube_style(clone_style_url.strip())
    else:
        persona = get_channel_persona(channel_id, ms.get("language", "en"))
    if voice_sample:
        persona.voice_sample_path = voice_sample

    out_root = pkg / "phase2_output"
    manifest_path = out_root / "phase2_manifest.json"
    if fresh and manifest_path.exists():
        manifest_path.unlink()

    if manifest_path.exists():
        manifest = Phase2Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        print(f"[CHECKPOINT PHASE 2] Đã nạp tiến trình lưu tại {manifest_path.name}", flush=True)
    else:
        manifest = Phase2Manifest(
            run_id=ms.get("run_id", pkg.name),
            channel_id=persona.channel_id,
            source_package_dir=str(pkg),
            output_dir=str(out_root),
        )

    scenes = ms["scenes"][:max_scenes] if max_scenes > 0 else ms["scenes"]
    # Kiểm định chống lặp nội dung trước khi dựng hình/tiếng
    qa_pre = deduplicate_and_audit_scenes(scenes, similarity_threshold=0.55, drop_duplicates=True)
    if qa_pre["duplicates_removed"] > 0:
        print(
            f"[AGENT 06 QA INSPECTOR] Đã tự động lọc bỏ {qa_pre['duplicates_removed']} cảnh bị lặp nội dung "
            f"({', '.join(d['duplicate_scene_id'] + '==' + d['original_scene_id'] for d in qa_pre['duplicates'][:5])}).",
            flush=True,
        )
        scenes = qa_pre["cleaned_scenes"]
    total = len(scenes)
    print(f"\n{'='*70}", flush=True)
    print(f"[KHỞI ĐỘNG PHASE 2 PRODUCTION] Run: {manifest.run_id} | Kênh: {persona.channel_id} ({persona.niche})", flush=True)
    print(f"Số cảnh cần dựng: {total} | Giọng đọc: {persona.edge_voice} | Chế độ: {'LOCAL $0' if force_local else 'HYBRID CLOUD+M4'}", flush=True)
    print(f"{'='*70}\n", flush=True)

    voice_dir = out_root / "voice"
    visual_dir = out_root / "visual"
    motion_dir = out_root / "motion"

    for idx, sc in enumerate(scenes, 1):
        sid = sc["scene_id"]
        # 1. AGENT VOICE
        if sid in manifest.voice_outputs and Path(manifest.voice_outputs[sid].audio_path).exists():
            v_out = manifest.voice_outputs[sid]
        else:
            v_out = synthesize_scene_voice(sc, voice_dir, persona, force_local=force_local)
            manifest.voice_outputs[sid] = v_out
            _save_manifest(manifest_path, manifest)

        # 2. AGENT VISUAL
        if sid in manifest.visual_outputs and Path(manifest.visual_outputs[sid].base_image_path).exists():
            vis_out = manifest.visual_outputs[sid]
        else:
            vis_out = generate_scene_visual(sc, visual_dir, persona, evidence_map=ev_map, force_local=force_local)
            manifest.visual_outputs[sid] = vis_out
            _save_manifest(manifest_path, manifest)

        # 3. AGENT MOTION
        if sid in manifest.motion_outputs and Path(manifest.motion_outputs[sid].video_clip_path).exists():
            m_out = manifest.motion_outputs[sid]
        else:
            m_out = render_scene_motion(sc, vis_out, v_out.duration_sec, motion_dir, force_local=force_local, voice_out=v_out)
            manifest.motion_outputs[sid] = m_out
            _save_manifest(manifest_path, manifest)

        print(
            f"  [{idx:03d}/{total:03d}] {sid} ({sc.get('visual_mode')}) | "
            f"Voice: {v_out.duration_sec:.1f}s ({v_out.engine_used}) | "
            f"Visual: {vis_out.provider_used} | Motion: {m_out.motion_engine}",
            flush=True,
        )

    # 4. AGENT COMPOSITOR (FINAL CUT)
    out_filename = f"preview_{total}_scenes.mp4" if max_scenes > 0 else "final_documentary.mp4"
    final_mp4 = out_root / out_filename
    print(f"\n--- [AGENT 4: MASTER COMPOSITOR] Đang hòa âm SFX, khắc phụ đề & xuất {out_filename}... ---", flush=True)
    compose_final_video(
        scenes=scenes,
        voice_outputs=manifest.voice_outputs,
        motion_outputs=manifest.motion_outputs,
        work_dir=out_root,
        final_mp4_path=final_mp4,
    )
    manifest.final_video_path = str(final_mp4)
    manifest.total_duration_sec = round(sum(manifest.voice_outputs[s["scene_id"]].duration_sec for s in scenes), 2)
    _save_manifest(manifest_path, manifest)

    # 5. AGENT 06: OUTPUT VIDEO & ANTI-REPETITION QA INSPECTOR
    qa_report_path = out_root / "qa_report.json"
    qa_res = audit_final_video(
        final_mp4=final_mp4,
        scenes=scenes,
        voice_outputs=manifest.voice_outputs,
        motion_outputs=manifest.motion_outputs,
        out_report_path=qa_report_path,
    )

    print(f"\n{'='*70}", flush=True)
    print(f"HOÀN TẤT GIAI ĐOẠN 2! Video thành phẩm: {final_mp4}", flush=True)
    print(f"Phụ đề chuẩn YouTube (.srt)      : {final_mp4.with_suffix('.srt')}", flush=True)
    print(f"Tổng thời lượng thực tế          : {qa_res['actual_video_duration_sec']}s (Dự kiến: {qa_res['expected_voice_duration_sec']}s | Lệch: {qa_res['sync_drift_sec']}s)", flush=True)
    print(f"Kiểm định QA (Agent 06)          : {qa_res['qa_status']} | Báo cáo: {qa_report_path.name}", flush=True)
    for w_msg in qa_res.get("warnings", []):
        print(f"  ⚠️ {w_msg}", flush=True)
    print(f"{'='*70}\n", flush=True)
    return final_mp4


def main():
    parser = argparse.ArgumentParser(description="Chạy toàn bộ Giai đoạn 2 (4 AI Agents) từ gói production_package")
    parser.add_argument("package_dir", help="Đường dẫn tới thư mục production_package/<run_id>")
    parser.add_argument(
        "--channel",
        default="med_forensic_us",
        choices=list(CHANNEL_PRESETS.keys()),
        help="Chọn hồ sơ kênh (tự động đổi giọng đọc, cảm xúc, màu phim)",
    )
    parser.add_argument("--voice-sample", default="", help="URL hoặc đường dẫn mẫu giọng (5-10s) để clone qua Chatterbox")
    parser.add_argument("--clone-style", default="", help="URL kênh hoặc video YouTube mẫu để tự động bóc tách & nhại theo style dựng phim")
    parser.add_argument("--max-scenes", type=int, default=0, help="Chỉ dựng N cảnh đầu (ví dụ --max-scenes 5 để xem nhanh Hook)")
    parser.add_argument("--local", action="store_true", help="Ép chạy hoàn toàn Local miễn phí ($0) trên Mac mini M4")
    parser.add_argument("--fresh", action="store_true", help="Xóa checkpoint Phase 2 và dựng lại từ cảnh S001")
    args = parser.parse_args()

    run_phase2_pipeline(
        package_dir=Path(args.package_dir),
        channel_id=args.channel,
        voice_sample=args.voice_sample,
        max_scenes=args.max_scenes,
        force_local=args.local,
        fresh=args.fresh,
        clone_style_url=args.clone_style,
    )


if __name__ == "__main__":
    main()
