"""UI Tabs mở rộng cho Faceless Studio Mission Control:
- Tab 0: Tổng quan Dự án (Realtime auto-refresh 3s + Thumbnail + Discord Alert)
- Tab 1: Niche Radar (Quét ngách nổ view 1-Click)
- Tab 3: Dựng Video (Phase 2 Producer + Checkpoint + Reroll từng cảnh)
- Tab 4: Agent QA & Xuất File (Kiểm định + Preview MP4 + Download)
"""
import json
import sys
import threading
from pathlib import Path
from typing import Dict

import streamlit as st

SCRIPT_WRITER_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_WRITER_DIR.parent
VIDEO_PRODUCER_DIR = WORKSPACE_ROOT / "agent_video_producer"

for p in (str(WORKSPACE_ROOT), str(VIDEO_PRODUCER_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from agent_06_qa_inspector.qa_inspector import audit_final_video  # noqa: E402
from run_phase2 import reroll_single_scene, run_phase2_pipeline  # noqa: E402
from shared.alerts import scan_all_projects, send_discord_alert  # noqa: E402
from shared.channels import CHANNEL_PRESETS  # noqa: E402
from shared.contracts import Phase2Manifest  # noqa: E402
from shared.env import get_env_key  # noqa: E402
from tools.niche_radar import scan_breakout_niches  # noqa: E402


PACKAGES_ROOT = SCRIPT_WRITER_DIR / "production_package"


def get_discord_webhook() -> str:
    if "discord_webhook_url" not in st.session_state:
        st.session_state.discord_webhook_url = get_env_key("DISCORD_WEBHOOK_URL", "")
    return st.session_state.discord_webhook_url


def launch_phase2_background(
    package_dir: Path,
    channel_id: str,
    max_scenes: int = 0,
    force_local: bool = False,
    fresh: bool = False,
    discord_webhook_url: str = "",
) -> None:
    """Khởi chạy Phase 2 ở luồng nền để UI Overview cập nhật realtime."""
    def _worker():
        try:
            run_phase2_pipeline(
                package_dir=package_dir,
                channel_id=channel_id,
                max_scenes=max_scenes,
                force_local=force_local,
                fresh=fresh,
                discord_webhook_url=discord_webhook_url,
            )
        except Exception:
            # Lỗi đã được ghi vào live_status.json và bắn về Discord trong run_phase2_pipeline
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def render_overview_tab() -> None:
    """Tab 0: Dashboard Tổng quan Realtime + Thumbnail + Discord Alert."""
    top_l, top_r = st.columns([3, 1])
    with top_l:
        wh_configured = bool(get_discord_webhook())
        with st.expander(f"🔔 Cảnh báo Discord Webhook ({'Đã cấu hình' if wh_configured else 'Chưa cấu hình'})", expanded=not wh_configured):
            c1, c2 = st.columns([3, 1])
            with c1:
                wh = st.text_input(
                    "Webhook URL",
                    value=get_discord_webhook(),
                    type="password",
                    placeholder="https://discord.com/api/webhooks/...",
                    key="discord_wh_input",
                    label_visibility="collapsed",
                )
                st.session_state.discord_webhook_url = wh.strip()
            with c2:
                if st.button("📨 Test Discord", use_container_width=True):
                    ok, detail = send_discord_alert(
                        webhook_url=st.session_state.discord_webhook_url,
                        title="✅ Faceless Studio: Kết nối Discord thành công",
                        message="Hệ thống sẽ tự động bắn cảnh báo vào kênh này ngay khi phát hiện lỗi ở Phase 1, Phase 2 hoặc Agent QA.",
                        level="success",
                    )
                    if ok:
                        st.success(f"OK ({detail})")
                    else:
                        st.error(f"Lỗi: {detail}")
    with top_r:
        auto_refresh = st.toggle("⚡ Realtime (3s)", value=True, key="overview_realtime_toggle")

    @st.fragment(run_every=3 if auto_refresh else None)
    def _live_grid():
        projects = scan_all_projects(PACKAGES_ROOT)
        total_cnt = len(projects)
        running_cnt = sum(1 for p in projects if p["status"] == "RUNNING")
        done_cnt = sum(1 for p in projects if p["status"] == "COMPLETED")
        err_cnt = sum(1 for p in projects if p["status"] in {"ERROR", "WARNING"})

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Tổng dự án", total_cnt)
        k2.metric("Đang chạy", running_cnt)
        k3.metric("Hoàn thành", done_cnt)
        k4.metric("Lỗi / QA Warning", err_cnt)

        if not projects:
            st.info("Chưa có dự án nào trong `production_package/`.")
            return

        cols = st.columns(3)
        for idx, proj in enumerate(projects):
            with cols[idx % 3]:
                with st.container(border=True):
                    if proj["thumbnail_path"] and Path(proj["thumbnail_path"]).exists():
                        st.markdown('<div class="studio-thumb">', unsafe_allow_html=True)
                        st.image(proj["thumbnail_path"], use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            "<div style='height:125px;border-radius:6px;background:#111827;border:1px dashed #334155;"
                            "display:flex;align-items:center;justify-content:center;color:#64748b;font-size:0.78rem;'>"
                            "🖼️ Chưa có ảnh preview</div>",
                            unsafe_allow_html=True,
                        )

                    status = proj["status"]
                    badge = {
                        "RUNNING": "🔵 CHẠY",
                        "COMPLETED": "🟢 XONG",
                        "WARNING": "🟠 QA WARN",
                        "ERROR": "🔴 LỖI",
                        "PAUSED": "🟡 TẠM DỪNG",
                        "PENDING": "⚪ CHỜ",
                    }.get(status, status)

                    st.markdown(f"**`{proj['run_id'][:24]}`** · {badge}")
                    st.caption(
                        f"`{proj['language'].upper()}` · `{proj['channel_id']}` · "
                        f"**{proj['done_scenes']}/{proj['total_scenes']}** ({proj['progress_pct']}%)"
                    )
                    st.progress(min(max(proj["progress_pct"] / 100.0, 0.0), 1.0))

                    if proj["error_msg"]:
                        st.error(proj["error_msg"][:120])

                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("📂 Mở", key=f"sel_{proj['run_id']}", use_container_width=True):
                            st.session_state.selected_phase2_pkg = proj["package_dir"]
                            st.toast(f"Đã chọn {proj['run_id']}")
                    with b2:
                        if status in {"ERROR", "PAUSED", "PENDING"}:
                            if st.button("▶️ Chạy tiếp", key=f"resume_{proj['run_id']}", use_container_width=True):
                                launch_phase2_background(
                                    package_dir=Path(proj["package_dir"]),
                                    channel_id=proj["channel_id"] if proj["channel_id"] in CHANNEL_PRESETS else "med_forensic_us",
                                    discord_webhook_url=get_discord_webhook(),
                                )
                                st.toast(f"Đang chạy tiếp {proj['run_id']}!")

    _live_grid()


def render_niche_radar_tab() -> None:
    """Tab 1: Quét ngách nổ view & ít đối thủ."""
    st.subheader("🎯 Niche Radar — Tìm ngách nổ View & Ít đối thủ")
    live_scan = st.checkbox("Quét trực tiếp từ YouTube (Live Scan)", value=False)
    if st.button("🔍 Quét Top Ngách Tiềm Năng", type="primary"):
        with st.spinner("Đang quét các ngách Outlier..."):
            st.session_state.radar_niches = scan_breakout_niches(live_youtube_scan=live_scan)

    niches = st.session_state.get("radar_niches", [])
    if not niches:
        st.info("Bấm **Quét Top Ngách Tiềm Năng** để xem danh sách video mồi có Outlier Score cao.")
        return

    for idx, n in enumerate(niches, 1):
        vid = n["selected_video"]
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**[{idx}] {n['niche_name']}**")
                st.caption(
                    f"RPM: `{n['rpm_range']}` | Cạnh tranh: `{n['competition_level']}` | "
                    f"Outlier: `{vid['outlier_score']}` | Kênh preset: `{n['channel_preset']}`"
                )
                st.write(f"Video mồi: [{vid['title']}]({vid['url']}) ({vid['views']:,} views)")
            with c2:
                if st.button("⚡ Đưa vào hàng đợi", key=f"pick_niche_{idx}", use_container_width=True):
                    st.session_state.radar_picked_url = vid["url"]
                    st.session_state.radar_picked_channel = n["channel_preset"]
                    st.success(f"Đã nạp URL & Preset `{n['channel_preset']}`!")


def _pick_package_dir() -> Path:
    projects = scan_all_projects(PACKAGES_ROOT)
    if not projects:
        return Path("")
    options = [p["package_dir"] for p in projects]
    default_pkg = st.session_state.get("selected_phase2_pkg", options[0])
    if default_pkg not in options:
        default_pkg = options[0]
    chosen = st.selectbox(
        "Chọn Package dự án:",
        options=options,
        index=options.index(default_pkg),
        format_func=lambda p: Path(p).name,
        key="phase2_pkg_selector",
    )
    st.session_state.selected_phase2_pkg = chosen
    return Path(chosen)


def render_phase2_video_tab() -> None:
    """Tab 3: Điều phối Phase 2 Video Producer (Voice -> Visual -> Motion -> Compositor)."""
    st.subheader("🎬 Dựng Video Tự Động (Phase 2 Producer)")
    pkg_dir = _pick_package_dir()
    if not pkg_dir or not (pkg_dir / "master_script.json").exists():
        st.info("Chưa có package kịch bản nào. Hãy chạy Phase 1 trước.")
        return

    ms = json.loads((pkg_dir / "master_script.json").read_text(encoding="utf-8"))
    scenes = ms.get("scenes") or []

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        preset_keys = list(CHANNEL_PRESETS.keys())
        default_ch = "ch20_dieu_tra_vn" if ms.get("language") == "vi" else "med_forensic_us"
        if default_ch not in preset_keys:
            default_ch = preset_keys[0]
        channel_id = st.selectbox("Channel Persona", preset_keys, index=preset_keys.index(default_ch))
    with c2:
        max_scenes = st.number_input("Số cảnh dựng (0 = tất cả)", min_value=0, max_value=max(len(scenes), 1), value=min(5, len(scenes)))
    with c3:
        force_local = st.checkbox("Chế độ Local $0", value=True)
    with c4:
        fresh = st.checkbox("Dựng lại từ đầu (Fresh)", value=False)

    b1, b2 = st.columns(2)
    with b1:
        if st.button("🚀 Chạy Phase 2 (Nền Realtime)", type="primary", use_container_width=True):
            launch_phase2_background(
                package_dir=pkg_dir,
                channel_id=channel_id,
                max_scenes=int(max_scenes),
                force_local=force_local,
                fresh=fresh,
                discord_webhook_url=get_discord_webhook(),
            )
            st.success("Đã đẩy Phase 2 vào luồng nền! Theo dõi tiến độ realtime ở Tab Tổng quan.")
    with b2:
        if st.button("▶️ Chạy tiếp từ Checkpoint", use_container_width=True):
            launch_phase2_background(
                package_dir=pkg_dir,
                channel_id=channel_id,
                max_scenes=int(max_scenes),
                force_local=force_local,
                fresh=False,
                discord_webhook_url=get_discord_webhook(),
            )
            st.info("Đang chạy tiếp các cảnh còn thiếu từ Checkpoint!")

    manifest_path = pkg_dir / "phase2_output" / "phase2_manifest.json"
    manifest = Phase2Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None

    st.markdown("---")
    st.markdown(f"**Danh sách cảnh ({len(scenes)} cảnh):**")
    preview_limit = st.slider("Số cảnh hiển thị", min_value=5, max_value=max(len(scenes), 5), value=min(15, len(scenes)))
    for sc in scenes[:preview_limit]:
        sid = sc["scene_id"]
        with st.container(border=True):
            sc_c1, sc_c2, sc_c3 = st.columns([3, 2, 1])
            with sc_c1:
                st.markdown(f"**{sid}** • `{sc.get('visual_mode', 'STATIC_2.5D_PARALLAX')}`")
                st.caption(sc.get("voiceover_text", "")[:180])
                if manifest and sid in manifest.voice_outputs:
                    v = manifest.voice_outputs[sid]
                    if Path(v.audio_path).exists():
                        st.audio(v.audio_path)
            with sc_c2:
                if manifest and sid in manifest.visual_outputs:
                    vis = manifest.visual_outputs[sid]
                    if Path(vis.base_image_path).exists():
                        st.image(vis.base_image_path, width=220)
                if manifest and sid in manifest.motion_outputs:
                    m = manifest.motion_outputs[sid]
                    st.caption(f"Motion: `{m.motion_engine}` ({m.duration_sec:.1f}s)")
            with sc_c3:
                if st.button("🔄 Reroll", key=f"reroll_p2_{pkg_dir.name}_{sid}", use_container_width=True):
                    with st.spinner(f"Đang dựng lại {sid}..."):
                        reroll_single_scene(
                            package_dir=pkg_dir,
                            scene_id=sid,
                            channel_id=channel_id,
                            force_local=force_local,
                            discord_webhook_url=get_discord_webhook(),
                        )
                    st.success(f"Đã reroll {sid}!")
                    st.rerun()


def render_qa_output_tab() -> None:
    """Tab 4: Agent 06 QA Inspector & Trình phát Video thành phẩm."""
    st.subheader("🛡️ Agent 06: QA Inspector & Thành Phẩm")
    pkg_dir = _pick_package_dir()
    if not pkg_dir:
        st.info("Chưa có package nào.")
        return

    out_root = pkg_dir / "phase2_output"
    qa_path = out_root / "qa_report.json"
    manifest_path = out_root / "phase2_manifest.json"

    if st.button("🔍 Chạy lại kiểm định Agent QA", type="primary"):
        if manifest_path.exists() and (pkg_dir / "master_script.json").exists():
            ms = json.loads((pkg_dir / "master_script.json").read_text(encoding="utf-8"))
            manifest = Phase2Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
            final_mp4 = Path(manifest.final_video_path) if manifest.final_video_path else (out_root / "final_documentary.mp4")
            rep = audit_final_video(
                final_mp4=final_mp4,
                scenes=ms.get("scenes", []),
                voice_outputs=manifest.voice_outputs,
                motion_outputs=manifest.motion_outputs,
                out_report_path=qa_path,
                discord_webhook_url=get_discord_webhook(),
            )
            st.success(f"Đã kiểm định xong: {rep['qa_status']}")
        else:
            st.warning("Chưa có `phase2_manifest.json` để kiểm định.")

    if not qa_path.exists():
        st.info("Chưa có `qa_report.json`. Hãy dựng video ở Tab Dựng Video hoặc bấm Chạy lại kiểm định.")
        return

    rep: Dict = json.loads(qa_path.read_text(encoding="utf-8"))
    status = rep.get("qa_status", "UNKNOWN")
    if status == "PASSED":
        st.success(f"QA STATUS: **{status}**")
    else:
        st.warning(f"QA STATUS: **{status}**")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Sync Drift (Audio vs MP4)", f"{rep.get('sync_drift_sec', 0)}s")
    m2.metric("Cảnh lặp phát hiện", len(rep.get("duplicate_scenes_detected", [])))
    m3.metric("Clip rỗng / lỗi", len(rep.get("empty_motion_clips", [])))
    m4.metric("Dung lượng MP4", f"{rep.get('file_size_mb', 0)} MB")

    if rep.get("warnings"):
        for w in rep["warnings"]:
            st.error(f"⚠️ {w}")

    srt_audit = rep.get("srt_audit") or {}
    if srt_audit:
        st.caption(f"Phụ đề `.srt`: **{srt_audit.get('blocks', 0)} blocks** | Chồng lấn: **{srt_audit.get('overlaps', 0)}**")

    final_mp4 = Path(rep.get("final_mp4", ""))
    if final_mp4.exists() and final_mp4.stat().st_size > 1000:
        st.video(str(final_mp4))
        d1, d2, d3 = st.columns(3)
        with d1:
            st.download_button("⬇️ Tải .MP4", data=final_mp4.read_bytes(), file_name=final_mp4.name, mime="video/mp4", use_container_width=True)
        srt_file = final_mp4.with_suffix(".srt")
        with d2:
            if srt_file.exists():
                st.download_button("⬇️ Tải .SRT", data=srt_file.read_bytes(), file_name=srt_file.name, mime="text/plain", use_container_width=True)
        with d3:
            st.download_button("⬇️ Tải qa_report.json", data=qa_path.read_bytes(), file_name="qa_report.json", mime="application/json", use_container_width=True)

    with st.expander("📄 Chi tiết qa_report.json", expanded=False):
        st.json(rep)
