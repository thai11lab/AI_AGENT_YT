# ĐẶC TẢ KỸ THUẬT CẤP ĐỘ STUDIO: FACELESS VIDEO AI AGENT
## GIAI ĐOẠN 1 — BỘ NÃO NGHIÊN CỨU, PHẢN BIỆN & ĐẠO DIỄN KỊCH BẢN (THE BRAIN v2.0)

---

## 1. GIẢI QUYẾT 4 "TỬ HUYỆT" KHIẾN OUTPUT CỦA AI BỊ KÉM CHẤT LƯỢNG

Hầu hết các hệ thống tự động hóa thất bại vì yêu cầu LLM đọc một đống tài liệu rồi xuất toàn bộ kịch bản JSON trong **1 lần gọi API duy nhất (Single-Shot Generation)**. Để đầu ra đạt chất lượng ngang ngửa biên kịch con người tại các kênh triệu view (*Lemmino, Fern, MagnatesMedia, 역사한줌*), kiến trúc v2.0 này triệt tiêu 4 tử huyệt sau:

### 1.1. Tử huyệt 1: "Bẫy giới hạn Token" (Output Token Compression Trap)
* **Vấn đề:** Một video 15–20 phút cần khoảng $200 \text{ đến } 250$ phân cảnh (scenes). Nếu xuất toàn bộ ra JSON chi tiết, dung lượng đầu ra lên tới $\sim 25.000 \text{ tokens}$, vượt quá giới hạn đầu ra tối đa trong 1 lần trả lời của hầu hết các model ($8.192 \text{ tokens}$). Khi bị ép xuất 1 lần, AI sẽ tự động viết cẩu thả, rút ngắn câu chữ và lặp lại prompt hình ảnh từ phân cảnh thứ 30 trở đi.
* **Giải pháp v2.0 (Act-by-Act Rolling Generation):** Chia kịch bản thành **5 Hồi (5 Acts)**. Agent sẽ lập Dàn ý Tổng thể (Master Beat Sheet) trước, sau đó chạy vòng lặp sinh chi tiết từng Hồi một ($35 \text{ đến } 45$ cảnh/lần gọi), truyền ngữ cảnh cảnh cuối của Hồi trước sang Hồi sau để mượt mà 100%.

### 1.2. Tử huyệt 2: Văn phong sáo rỗng mùi AI (AI-Slop & Cliché Prose)
* **Vấn đề:** AI rất thích dùng các từ sáo rỗng (*"delve into", "testament to", "a chilling reminder", "little did they know"*) làm người xem nhận ra ngay video rác và thoát ra.
* **Giải pháp v2.0 (Anti-Slop Lexicon & Script Doctor Node):** Thiết lập danh sách từ cấm (Blacklist) và một Node kiểm toán độc lập chỉ làm nhiệm vụ săn lùng các câu văn mượt mà giả tạo, ép viết lại thành câu ngắn, giàu động từ vật lý và danh từ cụ thể.

### 1.3. Tử huyệt 3: Mất tập trung ở phút thứ 3 (Mid-Video Retention Drop)
* **Vấn đề:** Có Hook 60 giây đầu tốt nhưng từ phút thứ 3 trở đi mạch truyện đều đều như đọc báo cáo.
* **Giải pháp v2.0 (Open-Loop Retention Architecture):** Cứ mỗi $90 \text{ đến } 120$ giây (tương đương cuối mỗi Hồi), kịch bản bắt buộc phải cài một **"Micro-Cliffhanger" (Vòng lặp mở)** — đặt ra một câu hỏi mới hoặc hé lộ một nghịch lý chưa giải thích ngay để kéo khán giả sang Hồi tiếp theo.

### 1.4. Tử huyệt 4: Hình ảnh rời rạc & Sai lệch Trigger Âm thanh
* **Vấn đề:** Cảnh trước và cảnh sau không ăn nhập về góc máy/ánh sáng; từ khóa kích hoạt âm thanh (`trigger_word`) do AI bịa ra không hề nằm trong câu thoại (`voiceover_text`), làm sập code ghép video ở Giai đoạn 3.
* **Giải pháp v2.0 (Self-Healing Pydantic Validators & Visual Bridges):** Dùng hàm kiểm tra tự động của Python (`@model_validator`) ép từ khóa SFX phải tồn tại chính xác trong câu thoại, cấm ký tự số trong lời đọc TTS, và bắt buộc mỗi cảnh phải có trường `visual_transition_from_prev` (cầu nối thị giác từ cảnh trước).

---

## 2. KIẾN TRÚC ĐỒ THỊ 7-NODE CHUYÊN SÂU (LANGGRAPH v2.0)

```text
[INPUT: Link YouTube Đối Thủ]
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 1: FORENSIC HACKER AGENT (yt-dlp + Groq Whisper v3 + FFmpeg)       │
│  ├─ Bóc băng chuẩn từng giây + Đo WPM từng phân đoạn                    │
│  ├─ Quét FFmpeg Scene Detection lấy nhịp độ đổi cảnh (Cut/phút)         │
│  └─ Cào 100 Comments (50 Top Liked + 50 Newest/Controversial)           │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 2: BLINDSPOT & COUNTER-THESIS PLANNER (Gemini 2.5 Pro)             │
│  ├─ Bóc tách luận điểm đối thủ & tìm điểm mù từ bình luận khán giả      │
│  └─ Thiết kế 4 Vector truy vấn chuyên sâu + Toán tử tìm kiếm nâng cao   │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 3: DEEP HARVESTER & FULL-TEXT SCRAPER (Exa + Tavily + Jina Reader) │
│  ├─ Tìm link báo cáo gốc, PDF, biên bản tòa án qua Exa/Tavily           │
│  ├─ Cào toàn văn (Full Markdown) các bài viết sâu bằng Jina Reader API  │
│  └─ Trích xuất Hồ sơ Điều tra có gắn Link Nguồn & Trích dẫn Nguyên văn  │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 4: HYBRID QUALITY GATEKEEPER (Python Math + Gemini 2.5 Pro)        │
│  ├─ Kiểm tra cứng bằng Code: Đếm số lượng số liệu, tên riêng, mốc giờ   │
│  ├─ Kiểm tra mềm bằng LLM: Đánh giá độ sắc bén của "Smoking Gun"        │
│  └─ Nếu Fail (< 8.5/10) ──► Quay lại NODE 3 đào đúng chỗ thiếu (Max 3x) │
└─────────────────────────────────────────────────────────────────────────┘
         │ (Pass >= 8.5/10)
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 5: NARRATIVE ARCHITECT & STYLE BIBLE (Claude 3.5 Sonnet)           │
│  ├─ Xây dựng Khung Xương 5 Hồi (5-Act Beat Sheet) + 4 Open Loops        │
│  └─ Khóa cứng StyleBible (Bảng màu, Lens, Từ điển Thực thể Cố định)     │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 6: ACT-BY-ACT SCENE DIRECTOR LOOP (Claude 3.5 Sonnet - Vòng lặp)   │
│  ├─ Chạy tuần tự từ Hồi 1 đến Hồi 5 (Mỗi hồi sinh 30-45 cảnh chi tiết)  │
│  ├─ Áp dụng Hybrid Motion: Hồi 1 = 100% Video AI; Hồi 2-5 = Tối ưu      │
│  └─ Tự động tách lớp Foreground/Midground/Background cho cảnh Parallax  │
└─────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ NODE 7: SCRIPT DOCTOR & ANTI-SLOP AUDITOR (Claude 3.5 Sonnet + Pydantic)│
│  ├─ Quét và tiêu diệt toàn bộ từ vựng AI sáo rỗng (Banned Lexicon)      │
│  ├─ Chuẩn hóa 100% số thành chữ cho TTS & Kiểm tra khớp Trigger Words   │
│  └─ Xuất file hoàn chỉnh: Master_Production_Script_v2.json              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. CÔNG THỨC TOÁN HỌC KIỂM ĐỊNH CHẤT LƯỢNG TỰ ĐỘNG

Trước khi cho phép dữ liệu đi qua Node tiếp theo, hệ thống áp dụng 3 công thức định lượng bằng code Python thuần kết hợp LLM:

### 3.1. Chỉ số Mật độ Thông tin Cụ thể ($IDS - \text{Information Density Score}$)
Tại Node 4, một Hồ sơ Điều tra (`ForensicDossier`) chỉ được thông qua nếu đạt điểm định lượng:

$$IDS = 0.30 \times \min\left(\frac{N_{\text{timestamps}}}{10}, 1\right) + 0.30 \times \min\left(\frac{N_{\text{metrics}}}{15}, 1\right) + 0.25 \times \min\left(\frac{N_{\text{artifacts}}}{12}, 1\right) + 0.15 \times \min\left(\frac{N_{\text{quotes}}}{5}, 1\right)$$

Trong đó:
* $N_{\text{timestamps}}$: Số mốc thời gian có ngày/giờ cụ thể (Yêu cầu tối thiểu $\ge 10$).
* $N_{\text{metrics}}$: Số lượng con số định lượng chính xác như tiền tệ, nhiệt độ, khoảng cách, mã hiệu (Yêu cầu $\ge 15$).
* $N_{\text{artifacts}}$: Số lượng vật thể/hiện vật vật lý có mô tả hình dáng, nhãn hiệu, chất liệu (Yêu cầu $\ge 12$).
* $N_{\text{quotes}}$: Số lượng trích dẫn nguyên văn từ nhân chứng hoặc tài liệu gốc (Yêu cầu $\ge 5$).
* **Điều kiện qua trạm:** $IDS \ge 0.85$.

### 3.2. Công thức Nhịp độ & Độ biến thiên Câu ($Burstiness$)
Để giọng đọc TTS nghe cuốn hút như người thật, độ dài câu trong mỗi Hồi không được đều nhau. Độ lệch chuẩn độ dài câu ($\sigma_L$) trên tập hợp $k$ câu trong một Hồi phải thỏa mãn:

$$\sigma_L = \sqrt{\frac{1}{k} \sum_{i=1}^{k} \left(L_i - \bar{L}\right)^2} \ge 4.5 \text{ từ}$$

*(Nghĩa là phải đan xen các câu dài $18 \text{ đến } 22$ từ mô tả bối cảnh với các câu cực ngắn $3 \text{ đến } 5$ từ tạo cú đấm cảm xúc, ví dụ: "Everything stopped.", "The vault was empty.")*

### 3.3. Quy đổi Thời lượng & Khung hình Chuẩn ($FPS = 30$)
Mỗi phân cảnh thứ $j$ có số từ là $W_j$ và hệ số tốc độ đọc theo giai đoạn là $R_{\text{phase}}$ (Hook: $2.7\text{ từ/giây}$, Setup/Escalation: $2.4\text{ từ/giây}$, Climax: $2.8\text{ từ/giây}$):

$$T_j = \frac{W_j}{R_{\text{phase}}} + T_{\text{pause}} \quad (\text{với } T_{\text{pause}} \in [0.2\text{s}, 0.6\text{s}])$$

$$F_j = \text{round}\left(T_j \times 30\right) \text{ frames}$$

---

## 4. HỆ THỐNG PYDANTIC SCHEMAS TỰ SỬA LỖI (`core/schemas.py`)

Điểm ăn tiền nhất của thiết kế này là sử dụng `@model_validator` của Pydantic kết hợp với thư viện `instructor` hoặc `langchain`. Nếu Claude 3.5 Sonnet vi phạm bất kỳ quy tắc nào (dùng từ cấm, quên viết chữ cho con số, hoặc gán `trigger_word` không có trong câu thoại), Pydantic sẽ ném lỗi chi tiết trả ngược lại cho Claude tự sửa ngay lập tức.

```python
import re
from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Literal, Optional

# Danh sách từ vựng sáo rỗng của AI bị cấm tuyệt đối trong kịch bản
BANNED_AI_PHRASES = [
    "delve into", "testament to", "in the realm of", "little did they know",
    "a chilling reminder", "tapestry of", "buckle up", "without further ado",
    "in today's video", "shocked the world", "changed everything forever",
    "it is important to note", "fast forward to", "beacon of hope"
]

# =====================================================================
# 1. SCHEMAS CHO NODE 1, 2, 3, 4 (NGHIÊN CỨU & KIỂM ĐỊNH)
# =====================================================================
class SourcedFact(BaseModel):
    exact_timestamp_or_date: str = Field(description="Giờ, phút, ngày tháng cụ thể (VD: 08:19 AM, Feb 5, 2016)")
    location_and_environment: str = Field(description="Vị trí vật lý, ánh sáng, thời tiết, không gian")
    fact_statement: str = Field(description="Sự kiện xảy ra với danh từ riêng và động từ cụ thể")
    hard_metrics: str = Field(description="Số liệu chính xác, mã hiệu, số tiền, kích thước vật lý")
    verbatim_quote_or_record: Optional[str] = Field(description="Trích dẫn nguyên văn từ biên bản/nhân chứng nếu có")
    source_url: str = Field(description="URL nguồn xác thực")

class PhysicalArtifactSpec(BaseModel):
    artifact_id: str = Field(description="Mã định danh ngắn, VD: ART_PRINTER_01")
    name_and_model: str = Field(description="Tên và mẫu mã chính xác, VD: HP LaserJet 4000n network printer")
    visual_description: str = Field(description="Mô tả chi tiết hình dáng, màu sắc, vết xước, đèn báo để vẽ ảnh AI")
    historical_role: str = Field(description="Vai trò của vật thể này trong câu chuyện")

class ForensicDossier(BaseModel):
    topic_archetype: Literal["HISTORICAL", "TRUE_CRIME", "TECH_FAILURE", "FINANCE_HEIST", "SCIENCE_MYSTERY"]
    competitor_thesis_summary: str
    competitor_blindspots: List[str] = Field(min_length=3)
    the_smoking_gun_paradox: str = Field(
        description="Sự thật trớ trêu hoặc bằng chứng đắt giá nhất dùng làm trục xoay lật ngược kịch bản đối thủ"
    )
    chronological_evidence: List[SourcedFact] = Field(min_length=10)
    technical_or_procedural_steps: List[str] = Field(
        min_length=5,
        description="Giải thích từng bước cơ chế kỹ thuật/vật lý/tài chính diễn ra như thế nào"
    )
    physical_artifacts_registry: List[PhysicalArtifactSpec] = Field(min_length=8)

# =====================================================================
# 2. SCHEMAS CHO NODE 5 (KIẾN TRÚC SƯ DÀN Ý 5 HỒI & STYLE BIBLE)
# =====================================================================
class RecurringEntityLock(BaseModel):
    entity_token: str = Field(description="Mã khóa, VD: CHAR_CEO_01 hoặc LOC_VAULT_01")
    fixed_prompt_descriptor: str = Field(
        description="Cụm mô tả ngoại hình/kiến trúc cố định không đổi để chèn vào mọi prompt có thực thể này"
    )

class StyleBible(BaseModel):
    era_and_atmosphere: str = Field(description="Bối cảnh thời đại và không khí chủ đạo")
    color_palette_hex_and_grading: str = Field(
        description="Tông màu điện ảnh, VD: Desaturated Kodak 2383 film stock, deep obsidian shadows, sodium-vapor amber highlights"
    )
    lens_and_lighting_rules: str = Field(
        description="Quy tắc ống kính và ánh sáng, VD: 35mm anamorphic lens, Chiaroscuro side-lighting, subtle halation"
    )
    negative_prompt_global: str = Field(
        default="cartoon, anime, 3d render, plastic skin, modern smartphones in historical setting, watermark, text overlay, blurry, deformed hands, oversaturated"
    )
    entity_locks: List[RecurringEntityLock] = Field(min_length=4)

class ActOutline(BaseModel):
    act_number: int = Field(ge=1, le=5)
    act_title: str
    narrative_phase: Literal["HOOK_0_60S", "SETUP", "ESCALATION", "CLIMAX", "RESOLUTION_OUTRO"]
    target_scene_count: int = Field(ge=10, le=45)
    target_duration_sec: float
    core_story_beats: List[str] = Field(min_length=4)
    open_loop_cliffhanger: str = Field(
        description="Câu hỏi bỏ lửng hoặc cú twist ở giây cuối cùng của Hồi này để giữ chân người xem sang Hồi tiếp theo"
    )

class NarrativeArchitecturePlan(BaseModel):
    viral_titles: List[str] = Field(min_length=5)
    thumbnail_visual_hook: str
    thumbnail_text_max_3_words: str
    style_bible: StyleBible
    acts: List[ActOutline] = Field(min_length=5, max_length=5)

# =====================================================================
# 3. SCHEMAS CHO NODE 6 & 7 (CHI TIẾT PHÂN CẢNH & TỰ ĐỘNG KIỂM ĐỊNH)
# =====================================================================
class ParallaxLayerSpec(BaseModel):
    foreground_layer: str = Field(description="Vật thể tiền cảnh sát ống kính (tách nền trong suốt) để di chuyển nhanh")
    midground_subject: str = Field(description="Chủ thể chính ở trung cảnh")
    background_environment: str = Field(description="Hậu cảnh phía xa di chuyển chậm")

class CameraVector(BaseModel):
    movement_type: Literal["SLOW_PUSH_IN", "SLOW_PULL_BACK", "PAN_LEFT_TO_RIGHT", "TILT_UP", "HANDHELD_TENSION", "ORBIT_3D", "STATIC_LOCK"]
    focal_length_mm: Literal[16, 24, 35, 50, 85, 100]
    shot_scale: Literal["EXTREME_CLOSE_UP", "CLOSE_UP", "MEDIUM_SHOT", "WIDE_ESTABLISHING", "OVER_THE_SHOULDER", "TOP_DOWN_GOD_VIEW"]

class AudioCue(BaseModel):
    sfx_category: Literal["WHOOSH_TRANSITION", "SUB_BASS_DROP", "TENSION_RISER", "MECHANICAL_CLICK", "PAPER_FOLEY", "DIGITAL_GLITCH", "AMBIENT_DRONE"]
    trigger_word: str = Field(description="Từ đơn chính xác nằm trong voiceover_text để kích hoạt SFX")
    volume_db: float = Field(default=-6.0, description="Mức âm lượng từ -18.0dB đến 0.0dB")
    sfx_specific_prompt: str = Field(description="Mô tả âm thanh cụ thể để tìm trong kho hoặc sinh bằng ElevenLabs SFX")

class SceneItem(BaseModel):
    scene_id: str = Field(description="Mã cảnh, VD: ACT1_S01")
    act_number: int
    narrative_phase: Literal["HOOK_0_60S", "SETUP", "ESCALATION", "CLIMAX", "RESOLUTION_OUTRO"]
    visual_mode: Literal["AI_VIDEO_HIGH_COST", "STATIC_PARALLAX_LOW_COST", "DOCUMENT_HIGHLIGHT_ZOOM", "KINETIC_DATA_CARD"]
    
    # Text & Timing
    voiceover_text: str = Field(description="Lời đọc 10-22 từ, tuyệt đối không chứa chữ số (0-9) hay từ sáo rỗng")
    pause_after_sec: float = Field(ge=0.1, le=1.2, default=0.3, description="Khoảng nghỉ nhịp thở sau câu thoại")
    estimated_duration_sec: float
    target_frames_30fps: int
    
    # Visual Continuity & Generation
    visual_transition_from_prev: str = Field(description="Cách nối hình mượt mà từ cảnh trước sang cảnh này (Match-cut, ánh sáng, chuyển động)")
    camera_vector: CameraVector
    flux_base_image_prompt: str = Field(description="Prompt sinh ảnh 16:9 siêu chi tiết, tối thiểu 45 từ, đã nhúng mô tả từ StyleBible")
    video_motion_prompt: Optional[str] = Field(default=None, description="Prompt điều khiển chuyển động cho Kling/Luma/Runway")
    parallax_layers: Optional[ParallaxLayerSpec] = Field(default=None, description="Bắt buộc phải có nếu visual_mode là STATIC_PARALLAX_LOW_COST")
    
    # Audio
    bgm_mood_intensity: Literal["SILENT_DROP", "LOW_PULSE_20%", "RISING_TENSION_50%", "PEAK_CLIMAX_80%"]
    audio_cues: List[AudioCue] = Field(min_length=1, max_length=3)

    # -----------------------------------------------------------------
    # BỘ KIỂM ĐỊNH TỰ ĐỘNG (SELF-HEALING VALIDATORS)
    # -----------------------------------------------------------------
    @model_validator(mode="after")
    def validate_scene_quality_rules(self) -> "SceneItem":
        vo_lower = self.voiceover_text.lower()

        # 1. Cấm tuyệt đối chữ số (0-9) trong voiceover_text để TTS không đọc lỗi
        if re.search(r"\d", self.voiceover_text):
            raise ValueError(
                f"Scene {self.scene_id}: 'voiceover_text' chứa chữ số ({self.voiceover_text}). "
                "Bắt buộc phải viết toàn bộ số bằng chữ tiếng Anh (VD: 'nineteen ninety-eight')."
            )

        # 2. Cấm các cụm từ AI sáo rỗng (Banned Lexicon)
        for phrase in BANNED_AI_PHRASES:
            if phrase in vo_lower:
                raise ValueError(
                    f"Scene {self.scene_id}: Phát hiện cụm từ sáo rỗng bị cấm '{phrase}' trong voiceover_text. "
                    "Hãy viết lại bằng hình ảnh thực tế và động từ mạnh."
                )

        # 3. Kiểm tra trigger_word của SFX phải thực sự nằm trong voiceover_text
        clean_vo_words = set(re.findall(r"\b[a-z']+\b", vo_lower))
        for cue in self.audio_cues:
            clean_trigger = re.sub(r"[^a-z']", "", cue.trigger_word.lower())
            if clean_trigger not in clean_vo_words:
                raise ValueError(
                    f"Scene {self.scene_id}: trigger_word '{cue.trigger_word}' không tồn tại trong voiceover_text '{self.voiceover_text}'. "
                    "Hãy chọn đúng một từ có trong câu thoại."
                )

        # 4. Kiểm tra quy tắc 60 giây đầu bắt buộc dùng AI_VIDEO_HIGH_COST
        if self.narrative_phase == "HOOK_0_60S" and self.visual_mode != "AI_VIDEO_HIGH_COST":
            raise ValueError(
                f"Scene {self.scene_id}: Giai đoạn HOOK_0_60S bắt buộc phải đặt visual_mode = 'AI_VIDEO_HIGH_COST'."
            )

        # 5. Kiểm tra đủ dữ liệu cho từng chế độ hình ảnh
        if self.visual_mode == "AI_VIDEO_HIGH_COST" and not self.video_motion_prompt:
            raise ValueError(f"Scene {self.scene_id}: Thiếu 'video_motion_prompt' cho cảnh AI_VIDEO_HIGH_COST.")
        if self.visual_mode == "STATIC_PARALLAX_LOW_COST" and not self.parallax_layers:
            raise ValueError(f"Scene {self.scene_id}: Thiếu 'parallax_layers' cho cảnh STATIC_PARALLAX_LOW_COST.")

        # 6. Đảm bảo prompt sinh ảnh đủ chi tiết (>= 35 từ)
        if len(self.flux_base_image_prompt.split()) < 35:
            raise ValueError(
                f"Scene {self.scene_id}: 'flux_base_image_prompt' quá ngắn và sơ sài. "
                "Phải mô tả đầy đủ 5 lớp: Góc máy + Chủ thể + Hiện vật vật lý + Ánh sáng/Màu sắc + Ống kính."
            )

        return self
```

---

## 5. KỸ THUẬT VIẾT PROMPT ĐẠO DIỄN: SO SÁNH GOOD VS. BAD (FEW-SHOT EXAMPLES)

Để LLM hiểu rõ thế nào là "chất lượng cao", trong `core/prompts.py` bắt buộc phải đính kèm bảng đối chiếu **Kém (Bị cấm)** và **Xuất sắc (Chuẩn mực)** như dưới đây:

### 5.1. Đối chiếu Lời bình (Voiceover Writing)
| Tiêu chí | ❌ Bản Kém (Văn phong AI rập khuôn - BỊ LOẠI) | ✅ Bản Xuất Sắc (Phong cách Điện ảnh Sắc lạnh - ĐẠT CHUẨN) |
| :--- | :--- | :--- |
| **Cách mở đầu (Hook)** | *"In today's video, we will delve into the shocking story of how hackers stole millions from a bank in 2016."* | *"On the fourth floor of the Dhaka central reserve, an eighty-dollar plastic printer began jamming at exactly eight thirty-six P.M."* |
| **Cách tả dữ liệu** | *"The fire was very hot and damaged the ship's hull badly before the voyage."* | *"Behind bulkhead number six, three hundred tons of smoldering coal baked the wrought-iron hull to a brittle nine hundred degrees."* |
| **Nhịp điệu câu** | Các câu dài đều nhau, dùng nhiều mệnh đề quan hệ *"which led to..."*, *"making it..."* | Câu ngắn gãy gọn. Cắt bỏ trạng từ dư thừa. Đặt chi tiết đắt giá nhất ở từ cuối cùng của câu. |

### 5.2. Đối chiếu Prompt Sinh Ảnh & Chuyển động (Visual Engineering)
* ❌ **Prompt Kém (Tạo ra ảnh giả tạo mùi AI):**
  > `A hacker in a dark room looking at red error code on computer screen, cinematic lighting, 8k, hyperrealistic.`
* ✅ **Prompt Chuẩn 5 Lớp (Tạo ra khung hình phim tài liệu Netflix):**
  > `[Shot Scale] Extreme close-up macro low-angle shot. [Subject & Action] Trembling, sweat-glistened fingers of a forty-five-year-old Bangladeshi bank clerk pressing the green 'RESUME' button on a dusty beige HP LaserJet 4000n printer. [Environment & Artifacts] Jammed perforated continuous-feed SWIFT transaction paper curling out of the tray, dimly lit 2010s Dhaka office cubicle in the background. [Lighting & Color] Harsh flickering overhead fluorescent tube casting sickly green-cyan shadows, blinking red error LED illuminating the fingertips, desaturated Kodak 2383 color grading. [Lens & Texture] Shot on 35mm Panavision anamorphic lens, f/2.8 shallow depth of field, heavy 35mm organic film grain, documentary realism.`

---

## 6. MÃ NGUỒN TRIỂN KHAI VÒNG LẶP ĐA HỒI (`agents/director_agent.py`)

Đoạn code dưới đây giải quyết triệt để bài toán viết kịch bản dài 15–20 phút mà không bao giờ bị đứt gãy hay suy giảm chất lượng ở giữa video:

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from typing import List
from core.schemas import (
    ForensicDossier,
    NarrativeArchitecturePlan,
    SceneItem,
    ActOutline,
    StyleBible
)

class ActByActDirector:
    def __init__(self):
        # Sử dụng Claude 3.5 Sonnet với nhiệt độ vừa phải để vừa sáng tạo vừa tuân thủ schema
        self.llm = ChatAnthropic(
            model="claude-3-5-sonnet-latest",
            temperature=0.4,
            max_tokens=8192
        )

    def build_narrative_architecture(self, dossier: ForensicDossier) -> NarrativeArchitecturePlan:
        """Bước 1: Lập dàn ý 5 Hồi (Beat Sheet) và khóa StyleBible trước khi viết chi tiết"""
        structured_architect = self.llm.with_structured_output(NarrativeArchitecturePlan)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an Executive Documentary Showrunner.
Based on the ForensicDossier, design a 5-Act Narrative Architecture and a locked Visual StyleBible.
Rules:
- Act 1 MUST be the 60-second Hook (12-15 fast scenes) starting immediately with the Smoking Gun Paradox.
- Acts 2, 3, and 4 MUST each end with a powerful Open-Loop Cliffhanger question or twist.
- Define recurring characters and key locations inside StyleBible.entity_locks with exact physical descriptors."""),
            ("human", "Forensic Dossier:\n{dossier_json}")
        ])
        
        chain = prompt | structured_architect
        return chain.invoke({"dossier_json": dossier.model_dump_json(indent=2)})

    def generate_scenes_for_single_act(
        self,
        act: ActOutline,
        style_bible: StyleBible,
        dossier: ForensicDossier,
        previous_scene_context: str
    ) -> List[SceneItem]:
        """Bước 2: Sinh chi tiết phân cảnh cho TỪNG HỒI MỘT để đạt chất lượng tối đa"""
        
        class ActSceneBatch( (SceneItem.__bases__[0]) ): # Wrapper cho danh sách cảnh của 1 Hồi
            scenes: List[SceneItem]

        structured_scene_writer = self.llm.with_structured_output(ActSceneBatch)

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a Master Documentary Director executing Act {act_number}: {act_title}.
Write all scenes for this Act following these uncompromising rules:
1. CONTINUITY: Smoothly bridge from the previous act's final scene: {prev_context}
2. HYBRID MOTION BUDGET:
   - If narrative_phase is 'HOOK_0_60S', 100% of scenes MUST be 'AI_VIDEO_HIGH_COST'.
   - Otherwise, use 'STATIC_PARALLAX_LOW_COST' (with 3-layer separation), 'DOCUMENT_HIGHLIGHT_ZOOM', or 'KINETIC_DATA_CARD' for 75% of scenes, reserving 'AI_VIDEO_HIGH_COST' only for peak dramatic actions.
3. ENTITY LOCKING: Whenever a recurring character or location appears, copy-paste their exact descriptor from StyleBible.entity_locks into `flux_base_image_prompt`.
4. ZERO NUMBERS & ZERO SLOP: Write all numbers out in words. Never use banned AI clichés.
5. EXACT TRIGGER WORDS: Every AudioCue `trigger_word` MUST be an exact single word present in `voiceover_text`."""),
            ("human", """StyleBible:\n{style_bible}\n\nAct Blueprint:\n{act_outline}\n\nRelevant Forensic Facts:\n{dossier}""")
        ])

        chain = prompt | structured_scene_writer
        result = chain.invoke({
            "act_number": act.act_number,
            "act_title": act.act_title,
            "prev_context": previous_scene_context,
            "style_bible": style_bible.model_dump_json(),
            "act_outline": act.model_dump_json(),
            "dossier": dossier.model_dump_json()
        })
        return result.scenes

    def run_full_production_script(self, dossier: ForensicDossier) -> dict:
        """Hàm điều phối chạy toàn bộ 5 Hồi nối tiếp nhau"""
        architecture = self.build_narrative_architecture(dossier)
        all_scenes: List[SceneItem] = []
        prev_context = "OPENING FRAME OF THE DOCUMENTARY - START COLD IN MEDIA RES."

        for act in architecture.acts:
            act_scenes = self.generate_scenes_for_single_act(
                act=act,
                style_bible=architecture.style_bible,
                dossier=dossier,
                previous_scene_context=prev_context
            )
            all_scenes.extend(act_scenes)
            
            # Lưu lại ngữ cảnh của cảnh cuối cùng trong Hồi này để làm cầu nối sang Hồi sau
            last_scene = act_scenes[-1]
            prev_context = (
                f"Last Voiceover: '{last_scene.voiceover_text}' | "
                f"Last Visual: '{last_scene.flux_base_image_prompt}' | "
                f"Open Loop to resolve: '{act.open_loop_cliffhanger}'"
            )

        return {
            "architecture": architecture.model_dump(),
            "total_scenes": len(all_scenes),
            "total_duration_sec": sum(s.estimated_duration_sec for s in all_scenes),
            "scenes": [s.model_dump() for s in all_scenes]
        }
```

---

## 7. BẢNG TIÊU CHUẨN NGHIỆM THU ĐẦU RA (QUALITY BENCHMARK CHECKLIST)

Một file `Master_Production_Script_v2.json` sinh ra từ Giai đoạn 1 chỉ được coi là **Đạt chuẩn Xuất xưởng** sang Giai đoạn 2 khi vượt qua 6 bài kiểm tra tự động sau trên giao diện Streamlit:

| STT | Hạng mục Kiểm định | Ngưỡng Đạt Chuẩn (Pass Threshold) | Cơ chế Sửa tự động nếu Fail |
| :--- | :--- | :--- | :--- |
| **1** | **Mật độ Dữ kiện ($IDS$)** | $\ge 0.85$ ($\ge 10$ mốc giờ, $\ge 15$ số liệu, $\ge 8$ hiện vật) | Kích hoạt lại Node 3 với truy vấn chuyên biệt từ `Exa.ai` |
| **2** | **Kiểm tra Số & Ký hiệu trong TTS** | $0$ chữ số (`0-9`, `$`, `%`) tồn tại trong `voiceover_text` | Validator của Pydantic ép Claude viết lại thành chữ |
| **3** | **Kiểm tra Từ vựng AI Sáo rỗng** | $0$ cụm từ nằm trong `BANNED_AI_PHRASES` | Node 7 (Script Doctor) cắt bỏ và viết lại câu đó |
| **4** | **Đồng bộ Trigger Word cho SFX** | $100\%$ `trigger_word` khớp chính xác từ đơn trong câu thoại | Validator báo lỗi chỉ rõ từ bị lệch để LLM chọn lại |
| **5** | **Tỷ lệ Ngân sách Hybrid Motion** | Phút thứ nhất: $100\%$ Video AI; Phút $2 \to 15$: $\le 25\%$ Video AI | Kiểm tra theo tổng `estimated_duration_sec` của từng nhóm |
| **6** | **Độ sâu Prompt Hình ảnh** | Mọi `flux_base_image_prompt` đều $\ge 35$ từ & chứa mã màu `StyleBible` | Tự động nối chuỗi hậu tố từ `StyleBible` nếu thiếu |