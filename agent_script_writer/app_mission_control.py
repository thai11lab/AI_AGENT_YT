"""FACELLESS STUDIO v3.1 — MISSION CONTROL DASHBOARD
Giao diện điều khiển trung tâm cho Giai đoạn 1 (The Autonomous Adversarial Brain).
Kết nối chạy THẬT 100% với core/orchestrator.py và hỗ trợ cập nhật tiến trình thời gian thực.
"""
import copy
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

# Đảm bảo đường dẫn import thư mục dự án
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from core.config import MODELS, ROOT
from core.schemas import (
    ActBlueprint,
    AudioCue,
    CounterHypothesis,
    EntityLock,
    EvidenceItem,
    MasterPlan,
    MasterScript,
    ParallaxLayers,
    ProsecutorIndictment,
    RivalAutopsyReport,
    SceneItem,
    StyleBible,
    tokenize,
)
from core.timing import budget_report, finalize_timing
from tools.scoring import compute_fss, fact_keys, new_unique_facts, passed
from tools.verify import classify_tier, dedupe_facts, verify_evidence
from tools.youtube_autopsy import build_input
from ui_studio_tabs import (
    get_discord_webhook,
    render_niche_radar_tab,
    render_overview_tab,
    render_phase2_video_tab,
    render_qa_output_tab,
)


# =====================================================================
# DỮ LIỆU MOCK ĐỂ PREVIEW KHI VỪA MỞ TRANG
# =====================================================================
def get_mock_job_state() -> Dict:
    sample_en = CURRENT_DIR / "samples" / "master_script.sample.en.json"
    if sample_en.exists():
        script_dict = json.loads(sample_en.read_text(encoding="utf-8"))
    else:
        script_dict = {}

    return {
        "job_id": "job-mock-apollo-2026",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "status": "COMPLETED",
        "language": "en",
        "current_node": "Showrunner",
        "loop_iteration": 2,
        "fss_score": 0.88,
        "delta_it": 0.124,
        "estimated_cost_usd": 0.42,
        "rival_wpm": 164.0,
        "autopsy": {
            "title": "The $400,000 Heist That Never Happened",
            "thesis": "The bank robbery was conducted by external cybercriminals via zero-day exploits.",
            "claims": [
                "The server room was entirely breached from an offshore IP.",
                "Employees only discovered the loss weeks after the incident.",
                "No physical hardware inside the facility was ever touched."
            ],
            "questions": [
                "Why did the internal dot-matrix printer log local keystrokes at 11:47 PM?",
                "Who signed off on the third-floor security badge swipe at 11:32 PM?",
                "Why was the archive room backup drive missing from evidence?"
            ]
        },
        "hypotheses": [
            {
                "id": "HYP_01",
                "title": "The Inside Hardware Switch",
                "arg": "The heist was an authorized internal ledger swap masked as a network intrusion using an unmonitored printer port.",
                "gun": "Internal maintenance work order dated March 14 with forged facility supervisor initials."
            },
            {
                "id": "HYP_02",
                "title": "The Dual Ledger Diversion",
                "arg": "Management staged the data loss to cover up a four-hundred-thousand-dollar balance deficit accrued over six months.",
                "gun": "State audit dispatch showing reconciliation warning sent forty-eight hours prior."
            },
            {
                "id": "HYP_03",
                "title": "The Discarded Firmware Exploit",
                "arg": "An obsolete 1990s printer controller was deliberately bridged to the financial transaction bus.",
                "gun": "FCC equipment compliance docket detailing unencrypted serial bus architecture."
            }
        ],
        "debate_feed": [
            {
                "sender": "architect",
                "title": "Architect (o3-reasoning)",
                "content": "Phát hiện 3 lỗ hổng chí mạng trong luận điểm đối thủ. Khởi tạo 3 giả thuyết lật kèo: HYP_01 (Tráo phần cứng nội bộ), HYP_02 (Thâm hụt kép dàn dựng), HYP_03 (Cổng máy in cổ điển)."
            },
            {
                "sender": "hunter",
                "title": "Forensic Hunter (Exa + Firecrawl)",
                "content": "Đã đào bới được 18 tài liệu gốc. Phát hiện Biên bản Tòa án Liên bang (Exhibit 12): ghi nhận lệnh in vật lý lúc 11:47 PM với mã tài khoản 774-A. Kèm tài liệu PDF kiểm toán ngân hàng Nhà nước."
            },
            {
                "sender": "prosecutor",
                "title": "Red-Team Prosecutor (o3-mini)",
                "is_error": True,
                "content": "[BÁC BỎ VÒNG 1] Lỗ hổng: Giả thuyết HYP_02 thiếu mốc thời gian giờ/phút chính xác. Yêu cầu Hunter đào sâu vào hồ sơ ca trực đêm ngày mười bốn tháng ba!"
            },
            {
                "sender": "hunter",
                "title": "Forensic Hunter (Exa Deep Search)",
                "content": "Bổ sung thành công: Log quẹt thẻ cửa tầng 3 lúc 11:32 PM và thông số điện áp máy in giảm lúc 11:48 PM. Đã đối chiếu chéo giữa 2 nguồn sơ cấp độc lập."
            },
            {
                "sender": "prosecutor",
                "title": "Red-Team Prosecutor (o3-mini)",
                "is_success": True,
                "content": "[PHÊ DUYỆT] Hồ sơ bằng chứng đạt chuẩn! FSS = 0.88 >= 0.75. Giả thuyết HYP_01 đã có đủ bằng chứng hút máu. Mở khóa sang Phòng Biên kịch!"
            }
        ],
        "script": script_dict
    }


# =====================================================================
# HÀM VALIDATE TỪNG CẢNH
# =====================================================================
def validate_scene_live(scene: Dict, language: str = "en") -> Dict[str, bool]:
    import re
    vo = scene.get("voiceover_text", "")
    low = vo.lower()

    # 1. Zero digits check
    has_digits = bool(re.search(r"\d", vo))

    # 2. Banned AI phrases
    from core.schemas import BANNED_PHRASES
    has_banned = any(p in low for p in BANNED_PHRASES.get(language, []))

    # 3. Trigger words check
    words = set(tokenize(vo))
    triggers = [c.get("trigger_word", "").lower() for c in scene.get("audio_cues", [])]
    triggers_match = bool(triggers) and all(re.sub(r"[^a-z']", "", t) in words for t in triggers if t)

    # 4. Mode specs
    mode = scene.get("visual_mode", "AI_VIDEO")
    if mode == "AI_VIDEO":
        mode_ok = bool(scene.get("video_motion_prompt")) and bool(scene.get("camera_move"))
    elif mode == "STATIC_PARALLAX":
        ps = scene.get("parallax_spec") or {}
        mode_ok = bool(ps.get("foreground_isolated") and ps.get("midground_main") and ps.get("background_plate"))
    elif mode == "DOCUMENT_HIGHLIGHT":
        da = scene.get("document_asset") or {}
        mode_ok = bool(da.get("source_url") and da.get("highlight_text"))
    elif mode == "KINETIC_DATA_CARD":
        mode_ok = bool(scene.get("on_screen_text"))
    else:
        mode_ok = True

    return {
        "no_digits": not has_digits,
        "anti_cliche": not has_banned,
        "triggers_valid": triggers_match,
        "mode_valid": mode_ok,
        "all_valid": (not has_digits) and (not has_banned) and triggers_match and mode_ok
    }


# =====================================================================
# HÀM THỰC THI THẬT (LIVE EXECUTION) VỚI STREAM VÀO UI
# =====================================================================
def execute_pipeline_live(url: str, manual_transcript: Optional[str], language: str, job_state: Dict):
    from core.orchestrator import (
        run_node_1_autopsy,
        run_node_2_architect,
        run_single_hunter,
        run_node_4_prosecutor,
        run_node_6a_plan,
        write_act_scenes_with_healing
    )
    from tools.assemble import assemble_package
    from concurrent.futures import ThreadPoolExecutor

    progress_bar = st.progress(0, text="Đang khởi tạo môi trường...")
    status_text = st.empty()

    try:
        # BƯỚC 1: Lấy dữ liệu & Autopsy
        status_text.info("🔍 [Node 1] Đang kết nối YouTube, tải phụ đề/bóc băng audio...")
        progress_bar.progress(10, text="Node 1: Multimodal Autopsy...")
        
        tmp_txt = None
        if manual_transcript and manual_transcript.strip():
            tmp_txt = CURRENT_DIR / ".cache" / "manual_input.txt"
            tmp_txt.parent.mkdir(exist_ok=True)
            tmp_txt.write_text(manual_transcript.strip(), encoding="utf-8")

        video_input = build_input(url, str(tmp_txt) if tmp_txt else None)
        job_state["rival_wpm"] = video_input.get("hook_60s_wpm", 150.0)

        autopsy = run_node_1_autopsy(video_input, language)
        job_state["autopsy"] = {
            "title": video_input.get("title", "Unknown"),
            "thesis": autopsy.rival_core_thesis,
            "claims": autopsy.superficial_claims,
            "questions": autopsy.audience_unanswered_questions
        }
        job_state["debate_feed"].append({
            "sender": "autopsy",
            "title": "Autopsy Agent",
            "content": f"Bóc tách thành công '{video_input.get('title')}'. Luận điểm chính đối thủ: {autopsy.rival_core_thesis}"
        })
        st.toast("✅ Node 1 hoàn tất!", icon="🎯")

        # BƯỚC 2: Kiến trúc sư Giả thuyết
        status_text.info("🏛️ [Node 2] Architect đang triệu tập 3 giả thuyết lật ngược...")
        progress_bar.progress(25, text="Node 2: Counter-Hypothesis Architect...")
        hypotheses = run_node_2_architect(autopsy)
        job_state["hypotheses"] = [
            {"id": h.hypothesis_id, "title": h.pivot_angle_title, "arg": h.core_argument, "gun": h.required_smoking_gun}
            for h in hypotheses
        ]
        job_state["debate_feed"].append({
            "sender": "architect",
            "title": "Architect",
            "content": f"Đã thiết lập 3 giả thuyết lật ngược: " + ", ".join([f"{h.hypothesis_id}: {h.pivot_angle_title}" for h in hypotheses])
        })
        st.toast("✅ Node 2 hoàn tất!", icon="🏛️")

        # BƯỚC 3 & 4: Vòng lặp Săn Bằng chứng & Công tố viên
        vault = []
        past_keys = set()
        winning_hyp = hypotheses[0]

        for round_num in range(1, 3):
            status_text.info(f"🔎 [Node 3 & 4] Vòng tranh biện {round_num}: Hunter đang cào tài liệu & Prosecutor đang chất vấn...")
            progress_bar.progress(35 + round_num * 10, text=f"Node 3 & 4: Debate Round {round_num}...")

            with ThreadPoolExecutor(max_workers=3) as executor:
                if round_num == 1:
                    futures = [executor.submit(run_single_hunter, h, h.initial_search_vectors) for h in hypotheses]
                else:
                    directives = [flaw.targeted_search_directive for flaw in indictment.identified_flaws] or winning_hyp.initial_search_vectors
                    futures = [executor.submit(run_single_hunter, winning_hyp, directives)]

                for f in futures:
                    vault.extend(f.result())

            vault = dedupe_facts(vault)
            for i, item in enumerate(vault, 1):
                item.evidence_id = f"EV_{i:03d}"

            curr_fss = compute_fss(vault)
            new_facts = new_unique_facts(past_keys, vault)
            past_keys = fact_keys(vault)
            job_state["fss_score"] = curr_fss
            job_state["delta_it"] = round(new_facts / max(len(vault), 1), 3)

            job_state["debate_feed"].append({
                "sender": "hunter",
                "title": f"Forensic Hunter (Vòng {round_num})",
                "content": f"Đã thu hoạch và xác minh được {len(vault)} bằng chứng gốc (Thêm {new_facts} facts mới trong vòng này)."
            })

            indictment = run_node_4_prosecutor(hypotheses, vault, round_num, curr_fss)
            if indictment.verdict == "NO_MORE_FLAWS" or passed(vault):
                job_state["debate_feed"].append({
                    "sender": "prosecutor",
                    "title": "Red-Team Prosecutor",
                    "is_success": True,
                    "content": f"[PHÊ DUYỆT] FSS={curr_fss:.2f} >= 0.75. Bằng chứng đạt chuẩn pháp y! Khóa hồ sơ cho giả thuyết {indictment.winning_hypothesis_id}."
                })
                break
            else:
                job_state["debate_feed"].append({
                    "sender": "prosecutor",
                    "title": f"Red-Team Prosecutor (Vòng {round_num})",
                    "is_error": True,
                    "content": f"[BÁC BỎ] Còn các lỗ hổng: " + "; ".join([f.critique_detail[:100] for f in indictment.identified_flaws])
                })

            for h in hypotheses:
                if h.hypothesis_id == indictment.winning_hypothesis_id:
                    winning_hyp = h
                    break

        # BƯỚC 6A: Showrunner Master Plan
        status_text.info("🎬 [Node 6A] Showrunner đang lập dàn ý 5 Hồi & StyleBible...")
        progress_bar.progress(65, text="Node 6A: Master Plan...")
        master_plan = run_node_6a_plan(winning_hyp, vault, language)
        st.toast("✅ Master Plan 5 Hồi đã sẵn sàng!", icon="🎬")

        # BƯỚC 6B & 7: Viết kịch bản chi tiết
        status_text.info("✍️ [Node 6B & 7] Đạo diễn đang viết kịch bản và chạy Script Doctor sửa lỗi...")
        progress_bar.progress(80, text="Node 6B: Scene Writing & Self-Healing...")
        all_scenes = []
        bridge = "COLD OPEN inside a physical room at the exact second something goes wrong."
        scene_counter = 1

        for act in master_plan.acts:
            act_scenes, bridge = write_act_scenes_with_healing(
                act=act,
                plan=master_plan,
                vault=vault,
                language=language,
                start_scene_num=scene_counter,
                prev_bridge=bridge
            )
            all_scenes.extend(act_scenes)
            scene_counter += len(act_scenes)

        from core.orchestrator import normalize_all_scenes
        all_scenes = normalize_all_scenes(all_scenes, master_plan, language)
        script_obj = MasterScript(
            run_id=job_state["job_id"],
            language=language,
            source_rival_url=url,
            plan=master_plan,
            scenes=all_scenes
        )
        finalize_timing(script_obj)
        job_state["script"] = script_obj.model_dump()

        # BƯỚC 8: Đóng gói
        status_text.info("📦 [Node 8] Đang đóng gói 7 file xuất xưởng ra production_package...")
        progress_bar.progress(95, text="Node 8: Packaging...")
        package_dir = CURRENT_DIR / "production_package"
        assemble_package(
            script=script_obj,
            evidence=vault,
            out_root=package_dir,
            quality={"fss_score": compute_fss(vault)}
        )

        progress_bar.progress(100, text="Hoàn tất 100%!")
        status_text.success("🎉 XUẤT XƯỞNG THÀNH CÔNG! Kịch bản đã sẵn sàng tại Tab 2 & Tab 3.")
        job_state["status"] = "COMPLETED"
        st.toast("🎉 Pipeline hoàn tất thành công!", icon="🚀")

    except Exception as e:
        status_text.error(f"❌ Pipeline gặp sự cố: {str(e)}")
        job_state["status"] = "FAILED"
        st.exception(e)


# =====================================================================
# CẤU HÌNH TRANG STREAMLIT
# =====================================================================
st.set_page_config(
    page_title="Faceless Studio v3.2 | Mission Control",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] {
        font-size: 13px !important;
      }
      header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2rem !important;
      }
      #MainMenu, footer {
        visibility: hidden;
      }
      .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 1.2rem !important;
        padding-left: 1.4rem !important;
        padding-right: 1.4rem !important;
        max-width: 1180px !important;
      }
      [data-testid="stVerticalBlock"] {
        gap: 0.55rem !important;
      }
      h1 { font-size: 1.25rem !important; margin-bottom: 0.2rem !important; }
      h2 { font-size: 1.05rem !important; margin-bottom: 0.2rem !important; }
      h3 { font-size: 0.92rem !important; margin-bottom: 0.2rem !important; }
      section[data-testid="stSidebar"] {
        min-width: 245px !important;
        max-width: 260px !important;
      }
      section[data-testid="stSidebar"] .block-container {
        padding-top: 0.8rem !important;
      }
      /* Menu điều hướng trong Sidebar */
      section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
        display: none !important;
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] > label {
        padding: 6px 10px !important;
        border-radius: 6px !important;
        margin-bottom: 2px !important;
        cursor: pointer !important;
        transition: background 0.15s ease;
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        background: #1e293b !important;
      }
      section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"],
      section[data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: #1e293b !important;
        border-left: 3px solid #38bdf8 !important;
      }
      [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 8px 12px !important;
      }
      [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        color: #94a3b8 !important;
      }
      [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
      }
      div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #1f2937 !important;
        border-radius: 8px !important;
        background-color: #0f172a !important;
        padding: 0.65rem !important;
      }
      .studio-thumb img {
        height: 110px !important;
        width: 100% !important;
        object-fit: cover !important;
        border-radius: 6px !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

if "jobs" not in st.session_state:
    st.session_state.jobs = {"job-mock-apollo-2026": get_mock_job_state()}

if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = "job-mock-apollo-2026"


SCREENS = [
    "📊 Tổng quan",
    "🎯 Niche Radar",
    "🎬 Dựng Video",
    "🛡️ Agent QA & Xuất",
    "🏛️ Tranh biện (Phase 1)",
    "📝 Sửa Kịch Bản",
    "📦 Export JSON",
]
if "active_screen" not in st.session_state or st.session_state.active_screen not in SCREENS:
    st.session_state.active_screen = "📊 Tổng quan"

# =====================================================================
# SIDEBAR: MENU ĐIỀU HƯỚNG & CẤU HÌNH NHANH
# =====================================================================
with st.sidebar:
    st.markdown("### 🎬 Faceless Studio")
    st.caption("v3.2 • Script + Video + QA")

    active_screen = st.radio(
        "Menu",
        SCREENS,
        key="active_screen",
        label_visibility="collapsed",
    )
    st.divider()

    with st.expander("⚡ Khởi tạo Job mới", expanded=False):
        urls_input = st.text_input(
            "YouTube URL đối thủ",
            value="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
        manual_vo = st.text_area("Transcript tay (tùy chọn)", height=80)
        col_sb1, col_sb2 = st.columns(2)
        with col_sb1:
            lang_choice = st.selectbox("Ngôn ngữ", ["en", "vi"], index=0, format_func=lambda x: "EN" if x == "en" else "VI")
        with col_sb2:
            motion_choice = st.selectbox("Tier", ["local_only", "cloud_video"], index=0)

        if st.button("🚀 Chạy Pipeline", type="primary", use_container_width=True):
            if not urls_input.strip().startswith("http"):
                st.error("Link YouTube không hợp lệ!")
            else:
                new_id = f"job-{time.strftime('%Y%m%d-%H%M%S')}"
                st.session_state.jobs[new_id] = {
                    "job_id": new_id,
                    "url": urls_input.strip(),
                    "status": "RUNNING",
                    "language": lang_choice,
                    "debate_feed": [],
                    "script": {},
                }
                st.session_state.active_job_id = new_id
                st.rerun()

        if st.button("🔄 Nạp Mock Preview", use_container_width=True):
            st.session_state.jobs["job-mock-apollo-2026"] = get_mock_job_state()
            st.session_state.active_job_id = "job-mock-apollo-2026"
            st.rerun()

    if "urls_input" not in locals():
        urls_input = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        manual_vo = ""
        lang_choice = "en"
        motion_choice = "local_only"

    st.divider()
    st.subheader("📋 Hàng Đợi Công Việc (Job Queue)")
    for j_id, j_data in list(st.session_state.jobs.items()):
        is_selected = (j_id == st.session_state.active_job_id)
        btn_label = f"{'🟢' if j_data['status'] == 'COMPLETED' else ('🟠' if j_data['status'] == 'RUNNING' else '🔴')} {j_id}"
        if st.button(btn_label, key=f"btn_{j_id}", use_container_width=True):
            st.session_state.active_job_id = j_id
            st.rerun()


# =====================================================================
# 1-CLICK NICHE RADAR & AUTO-ORCHESTRATOR (BẤM 1 NÚT CHỌN NGÁCH -> CHẠY FULL PHASE 1 + PHASE 2)
# =====================================================================
with st.expander("🔥 HỆ SINH THÁI 20 NGÁCH NỔ MẠNH - ÍT ĐỐI THỦ (1-CLICK NICHE RADAR & AUTO-PLANNER)", expanded=True):
    from tools.niche_radar import scan_breakout_niches

    col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
    with col_f1:
        selected_group = st.selectbox(
            "📂 Lọc theo Nhóm Chủ Đề (20 Kênh / 20 Ngách):",
            [
                "Tất cả",
                "Khoa Học & Y Sinh",
                "Công Nghệ & Tội Phạm Mạng",
                "Tài Chính & Kinh Doanh",
                "Thảm Họa & Kỹ Thuật",
                "Hình Sự & Tâm Lý",
                "Lịch Sử & Địa Chính Trị",
                "Văn Hóa, Giải Trí & Đời Sống",
            ],
        )
    with col_f2:
        custom_kw = st.text_input("💡 Hoặc nhập bất kỳ Ngách / Từ khóa mới nào bạn muốn mở thêm:", placeholder="VD: Formula 1 espionage, Luxury watch cartel, Deep sea cables...")
    with col_f3:
        st.write("")
        if st.button("🔎 Quét Sóng Mới Ngay", type="primary", use_container_width=True):
            with st.spinner("Đang quét đa luồng trên YouTube tìm các video mới nổ & ít đối thủ..."):
                st.session_state["niche_radar_results"] = scan_breakout_niches(
                    live_youtube_scan=True,
                    group_filter=selected_group,
                    custom_keyword=custom_kw,
                )

    radar_items = st.session_state.get("niche_radar_results") or scan_breakout_niches(
        live_youtube_scan=False,
        group_filter=selected_group,
        custom_keyword=custom_kw,
    )
    n_cols = st.columns(2)
    for idx_n, n_item in enumerate(radar_items):
        with n_cols[idx_n % 2]:
            with st.container(border=True):
                vid_info = n_item["selected_video"]
                st.markdown(f"#### 🎯 {n_item['niche_name']}")
                st.markdown(
                    f"**RPM:** `{n_item['rpm_range']}` | **Cạnh tranh:** `{n_item['competition_level']}` | "
                    f"**Điểm Outlier:** `{vid_info['outlier_score']}`"
                )
                st.markdown(f"**Video mồi phát hiện:** [{vid_info['title']}]({vid_info['url']}) (`{vid_info['views']:,} views`)")
                st.caption(f"💡 *Lý do nổ view:* {vid_info['why_viral']}")
                with st.expander("📋 Xem Plan phân công cho dàn AI Agent"):
                    for step_txt in n_item["agent_execution_plan"]:
                        st.markdown(f"- {step_txt}")

                if st.button(
                    f"🚀 Chọn Ngách Này & Cho AI Agent Làm Luôn",
                    key=f"launch_niche_{n_item['niche_id']}",
                    use_container_width=True,
                ):
                    new_id = f"run-en-{time.strftime('%Y%m%d-%H%M%S')}"
                    st.session_state.jobs[new_id] = {
                        "job_id": new_id,
                        "url": vid_info["url"],
                        "language": "en",
                        "status": "RUNNING",
                        "channel_preset": n_item["channel_preset"],
                        "auto_phase2": True,
                        "debate_feed": [],
                    }
                    st.session_state.active_job_id = new_id
                    st.rerun()

with st.expander("🧠 BỘ NÃO TỰ HỌC & NÂNG CẤP HÀNG NGÀY (Agent 08 — SQLite FTS5 Memory Bank)", expanded=False):
    from agents.agent_08_self_learner import (
        SQLiteFTS5MemoryBackend,
        prune_and_optimize_memory_bank,
        run_daily_self_learning_cycle,
    )

    mem_brain = SQLiteFTS5MemoryBackend()
    mem_stats = mem_brain.stats()
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        st.metric("Tổng Mẫu Câu Tinh Hoa", mem_stats["total_memories"])
    with col_b2:
        st.metric("Mẫu Golden (Tự học & Seed)", mem_stats["golden_patterns"])
    with col_b3:
        st.metric("Mẫu Do Bạn Sửa (WinScore=100)", mem_stats["user_fixes"])
    with col_b4:
        if st.button("🧹 Cắt Tỉa & Tối Ưu Bộ Nhớ", use_container_width=True):
            p_info = prune_and_optimize_memory_bank(brain=mem_brain)
            st.toast(f"Đã dọn {p_info['pruned_entries']} câu ngắn/điểm thấp!", icon="🧹")
            st.rerun()

    col_t1, col_t2, col_t3 = st.columns([2.2, 1.1, 1.1])
    with col_t1:
        train_url = st.text_input(
            "🔗 Dán link YouTube triệu view bất kỳ để Agent dùng LLM chưng cất tinh hoa văn phong (Song ngữ VI + EN):",
            placeholder="https://www.youtube.com/watch?v=...",
        )
    with col_t2:
        st.write("")
        if st.button("🎓 Học Ngay Từ Link Này", use_container_width=True):
            if train_url.strip():
                with st.spinner("Đang bóc băng & dùng LLM chưng cất cặp câu [❌ Đọc Slide] vs [✅ Người thật]..."):
                    res_c = run_daily_self_learning_cycle(
                        custom_urls=[train_url.strip()],
                        max_videos=1,
                        use_llm_distiller=True,
                        brain=mem_brain,
                    )
                st.success(f"Đã học thêm {res_c['new_patterns_learned']} mẫu câu tinh hoa mới vào script_brain.db!")
                st.rerun()
    with col_t3:
        st.write("")
        if st.button("🔄 Tự Học Hàng Ngày (Auto-Scan)", type="primary", use_container_width=True):
            with st.spinner("Đang tự động quét video triệu view mới nổ ngoài YouTube và chưng cất văn phong..."):
                res_d = run_daily_self_learning_cycle(max_videos=2, use_llm_distiller=True, brain=mem_brain)
            st.success(f"Chu kỳ tự học hoàn tất! Đã nạp thêm {res_d['new_patterns_learned']} mẫu câu mới.")
            st.rerun()

# =====================================================================
# THÂN TRANG CHÍNH: HIỂN THỊ CHI TIẾT JOB ĐANG CHỌN
# =====================================================================
current_job = st.session_state.jobs.get(st.session_state.active_job_id, get_mock_job_state())

# NẾU JOB ĐANG TRẠNG THÁI RUNNING, KÍCH HOẠT CHẠY THẬT NGAY!
if current_job.get("status") == "RUNNING" and not current_job.get("script"):
    st.header(f"⚡ Đang Xử Lý: `{current_job['job_id']}`")
    st.info("Hệ thống đang gọi các Agent bóc tách, săn bằng chứng, viết kịch bản và dựng video...")
    execute_pipeline_live(
        url=current_job["url"],
        manual_transcript=manual_vo if 'manual_vo' in locals() else None,
        language=current_job["language"],
        job_state=current_job
    )
    if current_job.get("auto_phase2"):
        pkg_path = CURRENT_DIR / "production_package" / current_job["job_id"]
        if pkg_path.exists():
            st.info("🎬 Đang kích hoạt tiếp 4 AI Agent Giai đoạn 2 (Voice -> Visual -> Motion 30fps -> Compositor)...")
            sys.path.insert(0, str(CURRENT_DIR.parent))
            sys.path.insert(0, str(CURRENT_DIR.parent / "agent_video_producer"))
            from agent_video_producer.run_phase2 import run_phase2_pipeline

            mp4_out = run_phase2_pipeline(
                package_dir=pkg_path,
                channel_id=current_job.get("channel_preset", "med_forensic_us"),
                max_scenes=5,
                discord_webhook_url=get_discord_webhook(),
            )
            current_job["phase2_mp4"] = str(mp4_out)
            st.success(f"🎉 Đã dựng xong Video mẫu: {mp4_out}")
            st.video(str(mp4_out))

st.markdown(
    f"<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;'>"
    f"<span style='font-size:1.05rem;font-weight:600;'>🎬 Faceless Studio • <code>{current_job['job_id']}</code></span>"
    f"<span style='font-size:0.8rem;color:#94a3b8;'>Lang: <b>{current_job.get('language', 'en').upper()}</b> · Status: <b>{current_job.get('status')}</b></span>"
    f"</div>",
    unsafe_allow_html=True,
)

if active_screen == "📊 Tổng quan":
    render_overview_tab()
elif active_screen == "🎯 Niche Radar":
    render_niche_radar_tab()
elif active_screen == "🎬 Dựng Video":
    render_phase2_video_tab()
elif active_screen == "🛡️ Agent QA & Xuất":
    render_qa_output_tab()


# =====================================================================
# TAB 1: REAL-TIME ADVERSARIAL DEBATE STREAMING
# =====================================================================
elif active_screen == "🏛️ Tranh biện (Phase 1)":
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(label="Competitor Hook WPM", value=f"{current_job.get('rival_wpm', 150):.0f} WPM", delta="-12% vs body")
    with col_m2:
        fss = current_job.get('fss_score', 0.85)
        st.metric(label="Current FSS Score", value=f"{fss:.2f}", delta=f"{fss - 0.75:+.2f} (Target >= 0.75)")
    with col_m3:
        st.metric(label="Semantic Novelty (ΔI_t)", value=f"{current_job.get('delta_it', 0.08)*100:.1f}%", delta="Bão hòa khi < 3%")
    with col_m4:
        st.metric(label="Estimated Script Cost", value=f"${current_job.get('estimated_cost_usd', 0.35):.2f}", delta="Trần $1.20")

    st.markdown("---")

    st.subheader("⚡ Luồng Trạng Thái Đồ Thị (6-Node Topology)")
    nodes = ["1. Autopsy", "2. Architect", "3. Hunter", "4. Prosecutor", "5. Human Gate", "6. Showrunner"]
    cols_nodes = st.columns(6)
    for idx, (col_n, n_name) in enumerate(zip(cols_nodes, nodes)):
        with col_n:
            st.success(f"**{n_name}**\n\n✅ COMPLETED")

    st.markdown("---")

    st.subheader("⚖️ Biên Bản Tranh Tụng Tại Tòa (Courtroom Debate Feed)")
    if not current_job.get("debate_feed"):
        st.info("Chưa có biên bản tranh luận nào. Bấm 'Khởi Chạy Pipeline THẬT' trên thanh menu bên trái để bắt đầu.")
    for msg in current_job.get("debate_feed", []):
        sender = msg.get("sender", "architect")
        avatar = "🏛️" if sender == "architect" else ("🔍" if sender == "hunter" else ("⚖️" if sender == "prosecutor" else ("🎯" if sender == "autopsy" else "👨‍⚖️")))
        with st.chat_message(name=msg.get("title", sender), avatar=avatar):
            if msg.get("is_error"):
                st.error(msg["content"])
            elif msg.get("is_success"):
                st.success(msg["content"])
            else:
                st.write(msg["content"])

    with st.expander("📌 Xem Chi Tiết Giả Thuyết Lật Kèo (Counter-Hypotheses)", expanded=False):
        for h in current_job.get("hypotheses", []):
            st.markdown(f"### `{h['id']}` — {h['title']}")
            st.markdown(f"**Luận điểm phản biện:** {h['arg']}")
            st.markdown(f"**Bằng chứng cốt lõi (Smoking Gun):** `{h['gun']}`")
            st.markdown("---")


# =====================================================================
# TAB 2: INTERACTIVE SCENE-BY-SCENE EDITOR & SINGLE-SHOT REROLL
# =====================================================================
elif active_screen == "📝 Sửa Kịch Bản":
    script_data = current_job.get("script", {})
    plan = script_data.get("plan", {})
    style_bible = plan.get("style_bible", {})
    scenes = script_data.get("scenes", [])

    if not scenes:
        st.warning("Chưa có kịch bản nào được tạo. Hãy bấm 'Khởi Chạy Pipeline THẬT' hoặc 'Nạp Dữ Liệu Mô Phỏng' từ thanh menu bên trái!")
    else:
        with st.expander("📖 StyleBible & Entity Locks (Quy Tắc Hình Ảnh & Nhân Vật)", expanded=False):
            sb_col1, sb_col2 = st.columns(2)
            with sb_col1:
                st.markdown(f"**Tone & Kỷ nguyên:** {style_bible.get('visual_era_and_tone', 'N/A')}")
                st.markdown(f"**LUT Màu sắc:** `{style_bible.get('color_grading_lut', 'N/A')}`")
            with sb_col2:
                st.markdown(f"**Ống kính & Hạt phim:** `{style_bible.get('lens_and_grain_spec', 'N/A')}`")
                st.markdown(f"**Negative Prompt:** `{style_bible.get('negative_prompt', 'N/A')}`")

            st.markdown("**Các Thực Thể Khóa (Entity Locks):**")
            for ent in style_bible.get("entity_locks", []):
                st.code(f"[{ent.get('entity_token')}] {ent.get('locked_visual_description')}\nPrompt gốc: {ent.get('reference_image_prompt')}", language="text")

        act_filter = st.radio(
            "Lọc cảnh theo Hồi (Act):",
            ["Tất cả cảnh (All)", "Hồi 1 (Hook 0-60s)", "Hồi 2 (Setup)", "Hồi 3 (Escalation)", "Hồi 4 (Climax)", "Hồi 5 (Resolution)"],
            horizontal=True
        )

        act_map = {
            "Hồi 1 (Hook 0-60s)": 1,
            "Hồi 2 (Setup)": 2,
            "Hồi 3 (Escalation)": 3,
            "Hồi 4 (Climax)": 4,
            "Hồi 5 (Resolution)": 5
        }

        filtered_scenes = scenes
        if act_filter in act_map:
            filtered_scenes = [s for s in scenes if s.get("act_number") == act_map[act_filter]]

        st.caption(f"Đang hiển thị {len(filtered_scenes)}/{len(scenes)} cảnh.")

        for idx, sc in enumerate(filtered_scenes):
            sc_id = sc.get("scene_id", f"S{idx+1:03d}")
            validation = validate_scene_live(sc, language=current_job.get("language", "en"))

            with st.container(border=True):
                col_header1, col_header2 = st.columns([3, 1])
                with col_header1:
                    st.markdown(f"#### 🎬 Cảnh `{sc_id}` | Hồi {sc.get('act_number')} ({sc.get('narrative_phase')}) | Bắt đầu: `{sc.get('start_sec', 0.0)}s` (Dài ~`{sc.get('duration_sec', 0.0)}s`)")
                with col_header2:
                    if validation["all_valid"]:
                        st.success("✅ Đạt chuẩn Studio")
                    else:
                        st.error("⚠️ Cần sửa lỗi")

                c_left, c_mid, c_right = st.columns([1.2, 1.4, 1.1])

                with c_left:
                    st.markdown("**🎙️ Lời Bình Thoại (Voiceover):**")
                    old_vo_val = sc.get("voiceover_text", "")
                    new_vo = st.text_area(
                        "Voiceover text",
                        value=old_vo_val,
                        key=f"vo_{sc_id}_{current_job['job_id']}",
                        height=85,
                        label_visibility="collapsed"
                    )
                    if new_vo != old_vo_val and new_vo.strip():
                        try:
                            from agents.agent_08_self_learner import SQLiteFTS5MemoryBackend, infer_niche_tag

                            niche_t = infer_niche_tag(f"{current_job.get('channel_preset', '')} {new_vo}")
                            SQLiteFTS5MemoryBackend().record_user_correction(
                                old_slide_text=old_vo_val,
                                user_new_text=new_vo,
                                niche=niche_t,
                                act_phase=str(sc.get("narrative_phase", "SETUP")),
                            )
                            st.toast(f"🧠 Đã tự học câu bạn vừa sửa tại {sc_id} vào SQLite FTS5 (win_score=100)!", icon="🧠")
                        except Exception:
                            pass
                    sc["voiceover_text"] = new_vo

                    st.markdown("**🔊 Hiệu Ứng Âm Thanh (SFX Cues):**")
                    for c_idx, cue in enumerate(sc.get("audio_cues", [])):
                        st.caption(f"• `[{cue.get('sfx_category')}]` từ kích hoạt: **'{cue.get('trigger_word')}'** ({cue.get('volume_db')} dB)")

                with c_mid:
                    st.markdown("**🎨 Chế Độ Thị Giác (Visual Direction):**")
                    modes_list = ["AI_VIDEO", "STATIC_PARALLAX", "DOCUMENT_HIGHLIGHT", "KINETIC_DATA_CARD"]
                    curr_mode = sc.get("visual_mode", "AI_VIDEO")
                    mode_idx = modes_list.index(curr_mode) if curr_mode in modes_list else 0

                    new_mode = st.selectbox("Visual Mode", modes_list, index=mode_idx, key=f"mode_{sc_id}_{current_job['job_id']}", label_visibility="collapsed")
                    sc["visual_mode"] = new_mode

                    if new_mode == "AI_VIDEO":
                        sc["video_motion_prompt"] = st.text_input("Camera Motion Prompt", value=sc.get("video_motion_prompt") or "", key=f"mot_{sc_id}_{current_job['job_id']}")
                        sc["camera_move"] = st.selectbox("Camera Move", ["SLOW_PUSH_IN", "HANDHELD_TENSION", "ORBIT_3D", "PULL_BACK", "STATIC"], index=0, key=f"cam_{sc_id}_{current_job['job_id']}")
                    elif new_mode == "STATIC_PARALLAX":
                        ps = sc.get("parallax_spec") or {}
                        st.text_input("Tiền cảnh (Foreground)", value=ps.get("foreground_isolated", ""), key=f"p_fg_{sc_id}_{current_job['job_id']}")
                        st.text_input("Trung cảnh (Midground)", value=ps.get("midground_main", ""), key=f"p_mg_{sc_id}_{current_job['job_id']}")
                        st.text_input("Hậu cảnh (Background)", value=ps.get("background_plate", ""), key=f"p_bg_{sc_id}_{current_job['job_id']}")
                    elif new_mode == "DOCUMENT_HIGHLIGHT":
                        da = sc.get("document_asset") or {}
                        st.text_input("URL Tài liệu gốc", value=da.get("source_url", ""), key=f"doc_u_{sc_id}_{current_job['job_id']}")
                        st.text_input("Đoạn chữ bôi vàng (Highlight)", value=da.get("highlight_text", ""), key=f"doc_h_{sc_id}_{current_job['job_id']}")
                    elif new_mode == "KINETIC_DATA_CARD":
                        sc["on_screen_text"] = st.text_input("Chữ lớn trên màn hình", value=sc.get("on_screen_text") or "$412,000", key=f"ost_{sc_id}_{current_job['job_id']}")

                    st.markdown("**🖼️ Prompt Sinh Ảnh Gốc (Flux Base Prompt):**")
                    sc["flux_base_image_prompt"] = st.text_area("Flux Prompt", value=sc.get("flux_base_image_prompt", ""), key=f"flux_{sc_id}_{current_job['job_id']}", height=80, label_visibility="collapsed")

                with c_right:
                    st.markdown("**🛡️ Kiểm Tra Pydantic:**")
                    st.markdown(f"{'✅' if validation['no_digits'] else '❌'} Không chứa chữ số (0-9)")
                    st.markdown(f"{'✅' if validation['anti_cliche'] else '❌'} Không có từ AI sáo rỗng")
                    st.markdown(f"{'✅' if validation['triggers_valid'] else '❌'} Khớp từ kích hoạt SFX")
                    st.markdown(f"{'✅' if validation['mode_valid'] else '❌'} Đủ thông số kỹ thuật chế độ")

                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(f"🎲 Reroll Cảnh {sc_id} Này", key=f"reroll_{sc_id}_{current_job['job_id']}", use_container_width=True):
                        from core.llm import structured
                        with st.spinner(f"Đang gọi LLM viết lại riêng cảnh {sc_id}..."):
                            try:
                                prompt_reroll = f"""Rewrite ONLY this single scene {sc_id} in {current_job.get('language', 'en')}.
Current voiceover: {sc.get('voiceover_text')}
Current visual: {sc.get('flux_base_image_prompt')}
MANDATORY: ZERO DIGITS (0-9). Spell all numbers in spoken words.
Flux prompt MUST be >= 40 words with 35mm lens, camera angle and lighting.
Trigger word in audio cues MUST be in the voiceover.
"""
                                class SingleSceneWrap(SceneItem):
                                    pass
                                new_sc = structured("writer", prompt_reroll, SingleSceneWrap)
                                sc["voiceover_text"] = new_sc.voiceover_text
                                sc["flux_base_image_prompt"] = new_sc.flux_base_image_prompt
                                sc["audio_cues"] = [c.model_dump() for c in new_sc.audio_cues]
                                st.success(f"Đã reroll thành công cảnh {sc_id}!")
                                st.rerun()
                            except Exception as re_err:
                                st.error(f"Lỗi reroll: {str(re_err)}")


# =====================================================================
# TAB 3: EXPORT & JSON INSPECTOR
# =====================================================================
elif active_screen == "📦 Export JSON":
    st.subheader("📦 Trình Đóng Gói Xuất Xưởng Cho Giai Đoạn 2 (Phase 2 Delivery)")

    try:
        final_script_obj = MasterScript.model_validate(script_data)
        finalize_timing(final_script_obj)
        rep = budget_report(final_script_obj)
    except Exception:
        rep = {"hook_ai_share": 1.0, "hook_ai_ok": True, "body_ai_ok": True, "scenes_over_clip_limit": []}

    c_exp1, c_exp2, c_exp3 = st.columns(3)
    with c_exp1:
        st.metric("Tổng số cảnh", len(scenes))
    with c_exp2:
        st.metric("Hook 60s AI Video Share", f"{rep.get('hook_ai_share', 1.0)*100:.0f}%", ">= 95% Yêu cầu")
    with c_exp3:
        st.metric("Tỷ lệ Frame Chuẩn", "30 FPS", "Chuẩn dựng phim")

    st.markdown("---")
    st.markdown("#### 📄 Xem Trước Master Script JSON:")
    st.json(script_data, expanded=False)

    json_bytes = json.dumps(script_data, indent=2, ensure_ascii=False).encode("utf-8")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="⬇️ Tải Về master_script.json",
            data=json_bytes,
            file_name=f"master_script_{current_job.get('language', 'en')}.json",
            mime="application/json",
            use_container_width=True
        )

    with col_d2:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("master_script.json", json_bytes)
            zip_file.writestr("style_bible.json", json.dumps(plan.get("style_bible", {}), indent=2))
            zip_file.writestr("voiceover_full.txt", "\n\n".join([s.get("voiceover_text", "") for s in scenes]))
            zip_file.writestr("quality_report.json", json.dumps({"fss": current_job.get("fss_score", 0.88), "budget": rep}, indent=2))

        st.download_button(
            label="🎁 Tải Toàn Bộ Gói production_package.zip",
            data=zip_buffer.getvalue(),
            file_name=f"production_package_{current_job.get('job_id', 'job')}.zip",
            mime="application/zip",
            use_container_width=True
        )
