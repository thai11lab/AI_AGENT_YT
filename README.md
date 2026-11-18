# AI_AGENT_YT — Hệ Thống Sản Xuất Video Tài Liệu & Giải Trí Tự Hành (13 AI Agents)

Kiến trúc toàn hệ thống được phân tách rõ ràng theo đúng tên và nhiệm vụ của từng AI Agent qua 2 giai đoạn độc lập:

```text
AI_AGENT_YT/
├── docs/                                   # Tài liệu thiết kế kiến trúc & đặc tả kỹ thuật
├── run_one_click.py                        # [1-CLICK CLI] Chọn ngách -> Chạy tự động toàn bộ Giai đoạn 1 + 2
├── run_ui.sh                               # Khởi chạy Giao diện Web Mission Control (http://localhost:8501)
│
├── agent_script_writer/                    # === GIAI ĐOẠN 1: AGENT NGHIÊN CỨU, PHẢN BIỆN & VIẾT KỊCH BẢN ===
│   ├── app_mission_control.py              # Giao diện điều khiển Web (Streamlit UI)
│   ├── agents/                             # 8 AI Agents chuyên trách của Giai đoạn 1:
│   │   ├── agent_00_niche_radar/           # Agent 00: Săn ngách ít đối thủ & Video mới nổ (< 45 ngày)
│   │   ├── agent_01_autopsy/               # Agent 01: Tải phụ đề & Mổ xẻ luận điểm video đối thủ
│   │   ├── agent_02_architect/             # Agent 02: Kiến tạo 3 giả thuyết lật ngược (Counter-Hypothesis)
│   │   ├── agent_03_hunter/                # Agent 03: Truy lùng bằng chứng gốc (Tavily/PubMed) & xác minh trích dẫn
│   │   ├── agent_04_prosecutor/            # Agent 04: Công tố viên phản biện chéo & chấm điểm FSS (>= 0.75)
│   │   ├── agent_05_showrunner/            # Agent 05: Lập dàn ý 5 Hồi (MasterPlan) & khóa thực thể (StyleBible)
│   │   ├── agent_06_script_writer/         # Agent 06: Biên kịch chi tiết từng phân cảnh & tự động chữa lỗi
│   │   └── agent_07_packager/              # Agent 07: Đóng gói 7 file xuất xưởng + mã băm SHA-256
│   ├── core/                               # Lõi điều phối (orchestrator, schemas, llm router, timing)
│   ├── tools/                              # Công cụ nền (youtube_autopsy, forensic_search, verify, scoring)
│   ├── scripts/                            # CLI chạy Giai đoạn 1 (run_pipeline.py, validate_package.py)
│   └── production_package/                 # Thư mục chứa gói đầu ra chuẩn của từng Run ID
│
└── agent_video_producer/                   # === GIAI ĐOẠN 2: AGENT SẢN XUẤT ÂM THANH, ĐỒ HỌA & VIDEO ===
    ├── run_phase2.py                       # Bộ điều phối Giai đoạn 2 (có Checkpoint lưu từng cảnh)
    ├── shared/                             # Hợp đồng dữ liệu (contracts.py) & 20 Hồ sơ Kênh (channels.py)
    ├── agent_01_style_cloner/              # Agent 01 (P2): Bóc tách & sao chép DNA dựng phim từ kênh YouTube mẫu
    ├── agent_02_voice_tts/                 # Agent 02 (P2): Phòng thu giọng đọc cảm xúc, Clone giọng & đo timestamp từng từ
    ├── agent_03_visual_assets/             # Agent 03 (P2): Tạo ảnh 35mm (Flux), trang hồ sơ tài liệu & bảng số liệu
    ├── agent_04_motion_broll/              # Agent 04 (P2): Cắt Video B-Roll đúng ngữ cảnh & vẽ đồ họa 30fps
    └── agent_05_final_compositor/          # Agent 05 (P2): Hòa âm SFX theo trigger_word, phụ đề Karaoke & xuất .MP4
```

---

## Biểu Đồ Luồng Xử Lý Toàn Hệ Thống (System Flowchart)

```mermaid
flowchart TD
    subgraph P1["📁 CHẶNG 1: agent_script_writer (Nghiên cứu, Phản biện & Viết kịch bản)"]
        A0["Agent 00: Niche Radar<br/>(Tavily News 30d + yt-dlp Outlier)"] --> A1["Agent 01: Autopsy<br/>(yt-dlp Captions / Groq Whisper)"]
        A1 --> A2["Agent 02: Architect<br/>(DeepSeek-R1 / Gemini Pro - 3 Giả thuyết)"]
        A2 --> A3["Agent 03: Hunter<br/>(Tavily / Exa / PubMed / .gov)"]
        A3 --> A4{"Agent 04: Prosecutor<br/>(Chấm điểm FSS >= 0.75?)"}
        A4 -- "Chưa đạt (HUNT_DEEPER)" --> A3
        A4 -- "Đạt chuẩn (PASSED)" --> A5["Agent 05: Showrunner<br/>(Claude 3.7 Sonnet - 5 Hồi & StyleBible)"]
        A5 --> A6["Agent 06: Script Writer<br/>(Gemini 2.5 Flash + Pydantic Self-Healer)"]
        A6 --> A7["Agent 07: Packager<br/>(Timing + SHA-256 Checksum)"]
    end

    A7 --> PKG[("📦 Hợp Đồng Bàn Giao:<br/>production_package/&lt;run_id&gt;/<br/>(7 file JSON/TXT)")]

    subgraph P2["📁 CHẶNG 2: agent_video_producer (Âm thanh, B-Roll, Đồ họa 30fps & Render .MP4)"]
        PKG --> B1["Agent 01 (P2): Style Cloner<br/>(FFmpeg scdet + Pillow Histogram LUT)"]
        B1 --> B2["Agent 02 (P2): Voice TTS<br/>(Chatterbox / OpenAI / Edge-TTS + silenceremove)"]
        B2 --> B3["Agent 03 (P2): Visual Assets<br/>(Flux 35mm API + Pillow Document/Data Card)"]
        B3 --> B4["Agent 04 (P2): Motion & B-Roll<br/>(Pixabay/yt-dlp Slicer + 30fps Rawvideo Pipe)"]
        B4 --> B5["Agent 05 (P2): Final Compositor<br/>(PCM Wave Mixer + SFX Sync + H.264 .MP4)"]
    end

    B5 --> OUT(["🎬 Thành phẩm: final_documentary.mp4 + subtitles.srt"])
```
