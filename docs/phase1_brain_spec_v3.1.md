# ĐẶC TẢ GIAI ĐOẠN 1 (v3.1) — THE ADVERSARIAL BRAIN
**Mục tiêu duy nhất:** nhận 1 URL video đối thủ → xuất ra **`production_package/`** là đầu vào *không cần chỉnh tay* cho Giai đoạn 2 (sinh ảnh, video, TTS, SFX, ghép).

Thay đổi so với v3.0: sửa các lỗi chạy được (Hunter không có công cụ thật, thiếu Node 7, FSS do LLM tự chấm, cosine yếu), thêm **hợp đồng đầu ra Phase 2**, **bước xác minh nguồn**, **ngân sách mỗi run**, **cổng duyệt người**, và **lộ trình MVP**.

---

## 1. HỢP ĐỒNG ĐẦU RA (OUTPUT CONTRACT) — PHẦN QUAN TRỌNG NHẤT

> [!IMPORTANT]
> Phase 2 chỉ đọc thư mục này. Mọi thứ Phase 2 cần phải có sẵn ở đây. Nếu Phase 2 của bạn có yêu cầu input riêng (tên trường, độ phân giải, số khung hình…), sửa ở **mục 5 (schema)**, phần còn lại không đổi.

```text
production_package/<run_id>/
├── master_script.json        # Kịch bản cảnh-theo-cảnh (schema mục 5) — đầu vào chính
├── asset_manifest.json       # Danh sách tài nguyên Phase 2 phải sinh/lấy, theo thứ tự ưu tiên
├── style_bible.json          # Khóa phong cách + thực thể lặp lại (nhân vật, đạo cụ)
├── voiceover_full.txt        # Toàn bộ lời bình liền mạch (cho TTS, rồi cắt theo scene)
├── evidence_dossier.json     # Bằng chứng đã xác minh + URL + trích dẫn (để fact-check)
├── quality_report.json       # FSS, số nguồn, số cảnh, kiểm tra ngân sách, cờ cảnh báo
└── package_manifest.json     # schema_version, run_id, checksum các file, model đã dùng
```

### 1.1. Quy ước để Phase 2 tự động hóa được
| Quy ước | Giá trị | Lý do |
|---|---|---|
| `schema_version` | `"3.1"` | Phase 2 từ chối file sai phiên bản |
| Mã cảnh | `S001…S240` duy nhất, tăng dần | Khóa nối giữa ảnh/video/audio |
| Thời gian | Giây; `start_sec` cộng dồn từ `duration_sec` | Phase 2 dựng timeline không cần tính lại |
| Thời lượng cảnh | Ước tính `từ ÷ WPM + pause`; **Phase 2 ghi đè bằng thời lượng TTS thật** (`duration_source: "estimated"`) | TTS thật luôn lệch ước tính |
| Ảnh | 1 prompt gốc / cảnh + `reference_entities` | Phase 2 sinh ảnh tham chiếu thực thể trước, dùng làm reference cho mọi cảnh |
| Chữ trên màn hình | Trường `on_screen_text` riêng (**được dùng chữ số**) | Lời bình viết chữ cho TTS, màn hình hiển thị số |
| Tài liệu thật | `document_asset` có `source_url` + `highlight_text` | Phase 2 chụp/crop tài liệu thật, không để AI vẽ chữ |
| Cảnh AI Video | `video_motion_prompt` + `camera_move` + `video_duration_sec ≤ 8` | Giới hạn thực tế của model video |

### 1.2. Ví dụ 1 cảnh trong `master_script.json`
```json
{
  "scene_id": "S003",
  "act_number": 1,
  "narrative_phase": "HOOK",
  "start_sec": 11.4,
  "duration_sec": 5.8,
  "duration_source": "estimated",
  "voiceover_text": "At eleven forty seven the printer jammed. Nobody looked up.",
  "pause_after_sec": 0.3,
  "visual_mode": "AI_VIDEO",
  "flux_base_image_prompt": "Low angle 35mm lens, ... (>=40 từ, đã nhúng StyleBible)",
  "negative_prompt": "text, watermark, extra fingers",
  "reference_entities": ["CHAR_CLERK_01", "OBJ_PRINTER_01"],
  "video_motion_prompt": "slow push in on the jammed paper tray, red LED blinking",
  "camera_move": "SLOW_PUSH_IN",
  "video_duration_sec": 5.8,
  "parallax_spec": null,
  "document_asset": null,
  "on_screen_text": null,
  "visual_bridge_from_prev": "match cut: round wall clock to round printer dial",
  "audio_cues": [{"sfx_category": "MECHANICAL_FOLEY", "trigger_word": "jammed", "volume_db": -8, "sfx_generation_prompt": "..."}],
  "evidence_refs": ["EV_014"]
}
```

### 1.3. `asset_manifest.json` (Phase 2 đọc đầu tiên)
```json
{
  "entity_reference_images": [{"entity_token": "CHAR_CLERK_01", "prompt": "...", "priority": 1}],
  "document_assets": [{"asset_id": "DOC_001", "source_url": "...", "page": 15, "highlight_text": "...", "used_in_scenes": ["S120"]}],
  "counts": {"ai_video_scenes": 38, "parallax_scenes": 92, "document_scenes": 40, "data_card_scenes": 20, "total_scenes": 190},
  "estimated_total_duration_sec": 1010
}
```

---

## 2. KIẾN TRÚC (ĐÃ SỬA)

**Nguyên tắc:** LLM chỉ làm việc cần ngôn ngữ (phân tích, giả thuyết, phê bình, viết). **Mọi việc đo đếm, xác minh, định tuyến, kiểm tra ngân sách do code Python làm.**

```text
INPUT: rival URL
   │
   ▼
[N1 Autopsy]  yt-dlp + Groq Whisper + Gemini → RivalAutopsyReport
   │
   ▼
[N2 Architect]  3 giả thuyết ◄──────────────────────────────┐
   │ Send (song song)                                       │ DISCARD
   ▼                                                        │
[N3 Hunter x3]  Exa/Tavily → Firecrawl → LLM trích xuất     │
   │                                                        │
   ▼                                                        │
[N3b Verifier – CODE]  URL sống? trích dẫn có trong trang?  │
   │                    gán source_tier theo domain         │
   ▼                                                        │
[N3c Scorer – CODE]  FSS bằng công thức, dedupe fact,       │
   │                  new_facts_count, ngân sách run        │
   ▼                                                        │
[N4 Prosecutor – LLM]  chỉ nêu lỗ hổng + truy vấn đào sâu ──┘
   │ (route bằng CODE)
   ├─ còn lỗ hổng & còn ngân sách → quay lại N3 (Send)
   └─ đạt chuẩn / hết ngân sách → [N5 Dossier Lock]
                                      │
                           ★ HUMAN GATE (interrupt) ★  duyệt giả thuyết + dossier
                                      │
                                      ▼
[N6a Showrunner Plan]  Claude: 5 hồi + StyleBible + entity locks
   │
   ▼
[N6b Act Writer]  mỗi hồi chia lô ≤ 12 cảnh → Claude
   │
   ▼
[N7 Script Doctor]  validate từng cảnh → lỗi → retry ≤3 (chỉ cảnh lỗi)
   │
   ▼
[N8 Assembler – CODE]  tính start_sec, kiểm ngân sách theo THỜI LƯỢNG,
                       sinh asset_manifest, voiceover_full, quality_report
   ▼
OUTPUT: production_package/
```

### 2.1. Model & công nghệ (đặt qua `config/models.yaml`, **không hard-code**)
| Node | Vai trò | Công nghệ | Model (đổi được trong config) |
|---|---|---|---|
| N1 | Bóc băng + phân tích đối thủ | `yt-dlp`, `ffmpeg`, Groq Whisper, YouTube Data API | `whisper-large-v3-turbo` + Gemini Pro/Flash (Flash đủ cho bản đầu) |
| N2 | Giả thuyết đối nghịch | LangGraph | model suy luận (o3 / o4-mini / DeepSeek-R1) |
| N3 | Săn bằng chứng | Exa + Tavily + Firecrawl (hoặc Jina Reader) | Gemini Flash trích xuất **từ văn bản đã cào** |
| N3b/N3c/N5/N8 | Xác minh, chấm điểm, ghép gói | Python thuần | — (không LLM) |
| N4 | Công tố viên | structured output | model suy luận, khác họ với N2 nếu được |
| N6/N7 | Viết kịch bản + sửa | Anthropic SDK + Pydantic v2 | Claude Sonnet mới nhất |
| Hạ tầng | Trạng thái | LangGraph + `PostgresSaver` (dev: `SqliteSaver`) | — |
| Quan sát | Trace, chi phí | Langfuse hoặc LangSmith | — |

> [!NOTE]
> Bỏ Qdrant ở Giai đoạn 1: không có bước nào cần vector DB. Thêm khi cần nhớ chéo nhiều video.

---

## 3. CÔNG THỨC ĐIỀU KHIỂN (TÍNH BẰNG CODE)

### 3.1. FSS (Forensic Specificity Score) — tính từ dữ liệu đã xác minh
$$
FSS = \frac{1}{4}\Big[\min\!\big(\tfrac{C_{pri}}{3},1\big)+\min\!\big(\tfrac{C_{time}}{8},1\big)+\min\!\big(\tfrac{C_{met}}{10},1\big)+\min\!\big(\tfrac{C_{art}}{8},1\big)\Big]-P_{contra}
$$
- Chỉ đếm bằng chứng **đã qua Verifier** (trích dẫn có thật trong trang, URL truy cập được).
- Ngưỡng giảm so với v3.0 (3/8/10/8 thay vì 5/12/15/10) vì ngưỡng cũ gần như không đạt được với chủ đề thông thường. Hiệu chỉnh sau 3–5 lần chạy thử.
- `P_contra` = 0.1 × số mâu thuẫn chưa giải thích (tối đa 0.5), do Prosecutor liệt kê, code cộng.
- **Đạt chuẩn:** `FSS ≥ 0.75` và có ≥ 1 nguồn `PRIMARY` hoặc `ACADEMIC`.

### 3.2. Điều kiện dừng (thay cosine)
Dừng khi **một** điều kiện đúng, ghi `exit_reason` vào `quality_report`:
| `exit_reason` | Điều kiện | `quality_passed` |
|---|---|---|
| `PASSED` | FSS đạt chuẩn | true |
| `SATURATED` | `new_unique_facts < 3` ở 2 vòng liên tiếp | false |
| `MAX_ROUNDS` | vòng ≥ 4 | false |
| `BUDGET` | chi phí/thời gian run vượt `RUN_BUDGET` | false |

Nếu `quality_passed=false`, **Human Gate bắt buộc** hiển thị cảnh báo; các câu hỏi chưa có đáp án thành `unresolved_hooks` trong kịch bản (không bịa).
`new_unique_facts` = số fact còn lại sau dedupe (chuẩn hóa chuỗi + cosine ≥ 0.9 giữa *từng fact*, không phải cả vault).

### 3.3. Ngân sách Hybrid Motion — tính theo **thời lượng**
Thân video (`start_sec > 60`): tổng thời lượng cảnh `AI_VIDEO` ≤ 20% tổng thời lượng thân. Hook (`start_sec ≤ 60`): ≥ 95% thời lượng là `AI_VIDEO`.
Phân bổ thân video khuyến nghị (theo thời lượng): Parallax 45% · Document 20% · Data card 15% · AI Video ≤ 20%. N8 kiểm tra; nếu lệch, N7 yêu cầu **đổi `visual_mode` của các cảnh cụ thể**, không viết lại cả hồi.

### 3.4. Ngân sách mỗi run (`RUN_BUDGET`)
`max_usd=8`, `max_minutes=25`, `max_hunter_calls=24`, `max_scrape_pages=40`. Mỗi node ghi chi phí vào state; router kiểm tra trước mỗi vòng. (Số mặc định, chỉnh theo mục 10.)

---

## 4. XÁC MINH NGUỒN (N3b) — CHỐNG BỊA

1. Hunter **chỉ trích xuất từ văn bản Firecrawl trả về**; prompt cấm dùng kiến thức nền.
2. `verbatim_quote` phải là chuỗi con (đã chuẩn hóa khoảng trắng/dấu) của trang đã cào. Không khớp → bỏ fact.
3. `source_tier` do **code** gán theo domain/loại file (`.gov`, court, arxiv, `.pdf`…), LLM chỉ đề xuất.
4. Fact không có `source_url` hoặc quote → loại.
5. Cảnh trong kịch bản chỉ được trích `evidence_refs` có trong dossier (N7 kiểm tra).
6. Pháp lý: chỉ dùng ý tưởng/cấu trúc từ đối thủ, không chép văn; nhắc người thật chỉ theo nguồn công khai, dùng "bị cáo buộc / theo hồ sơ" khi chưa có phán quyết; xuất `disclosure_ai_generated=true`.

---

## 5. SCHEMAS (`core/schemas.py`)

```python
import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "3.1"
BANNED_AI_PHRASES = [
    "delve into", "testament to", "in the realm of", "little did they know",
    "a chilling reminder", "tapestry of", "buckle up", "without further ado",
    "in today's video", "shocked the world", "changed everything forever",
    "it is important to note", "fast forward to", "beacon of hope", "double-edged sword",
]
NARRATOR_WPM = 150  # Phase 2 sẽ ghi đè bằng thời lượng TTS thật

Tier = Literal["PRIMARY", "ACADEMIC", "JOURNALISM", "SECONDARY"]
VisualMode = Literal["AI_VIDEO", "STATIC_PARALLAX", "DOCUMENT_HIGHLIGHT", "KINETIC_DATA_CARD"]
Phase = Literal["HOOK", "SETUP", "ESCALATION", "CLIMAX", "RESOLUTION"]

# ---------- Nghiên cứu ----------
class RivalAutopsyReport(BaseModel):
    video_title: str
    hook_60s_wpm: float
    body_wpm: float
    cuts_per_minute_hook: float
    rival_core_thesis: str
    superficial_claims: List[str] = Field(min_length=1)
    audience_unanswered_questions: List[str] = Field(min_length=1)

class CounterHypothesis(BaseModel):
    hypothesis_id: str
    pivot_angle_title: str
    core_argument: str
    required_smoking_gun: str
    initial_search_vectors: List[str] = Field(min_length=3)

class HypothesisBatch(BaseModel):
    hypotheses: List[CounterHypothesis] = Field(min_length=3, max_length=3)

class EvidenceItem(BaseModel):
    evidence_id: str
    hypothesis_id: str
    source_url: str
    source_tier: Tier = "SECONDARY"             # code ghi đè
    exact_timestamp_or_date: Optional[str] = None
    physical_location: Optional[str] = None
    factual_claim: str
    quantitative_metric: Optional[str] = None
    verbatim_quote: str                          # bắt buộc, phải có trong trang gốc
    tangible_artifact_desc: Optional[str] = None
    verified: bool = False                       # chỉ code đặt True

class HarvestBatch(BaseModel):
    new_evidence: List[EvidenceItem]

class FlawCritique(BaseModel):
    flaw_type: Literal["LACK_OF_PRIMARY_SOURCE", "TIMELINE_CONTRADICTION",
                       "TOO_ABSTRACT_FOR_VISUAL", "CLICHE_ALREADY_KNOWN", "UNVERIFIED_NUMBER"]
    critique_detail: str
    targeted_search_directive: str
    search_engine_to_use: Literal["EXA_NEURAL", "TAVILY_DEEP", "FIRECRAWL_FULLTEXT"]

class ProsecutorIndictment(BaseModel):
    verdict: Literal["HUNT_DEEPER", "DISCARD_AND_RETHINK", "NO_MORE_FLAWS"]
    winning_hypothesis_id: str
    unexplained_contradictions: int = Field(ge=0, le=5)
    identified_flaws: List[FlawCritique]
    reasoning: str
    # KHÔNG có trường điểm số. FSS do code tính.

# ---------- Kịch bản (hợp đồng Phase 2) ----------
class EntityLock(BaseModel):
    entity_token: str = Field(pattern=r"^(CHAR|OBJ|LOC)_[A-Z0-9_]+$")
    locked_visual_description: str
    reference_image_prompt: str

class StyleBible(BaseModel):
    visual_era_and_tone: str
    color_grading_lut: str
    lens_and_grain_spec: str
    negative_prompt: str
    entity_locks: List[EntityLock] = Field(min_length=3)

class ActBlueprint(BaseModel):
    act_number: int = Field(ge=1, le=5)
    act_title: str
    narrative_phase: Phase
    target_scene_count: int = Field(ge=8, le=60)
    story_beats: List[str] = Field(min_length=3)
    open_loop_cliffhanger: str

class MasterPlan(BaseModel):
    selected_hypothesis_id: str
    viral_titles: List[str] = Field(min_length=5)
    thumbnail_concept: str
    style_bible: StyleBible
    acts: List[ActBlueprint] = Field(min_length=5, max_length=5)
    unresolved_hooks: List[str] = []

class ParallaxLayers(BaseModel):
    foreground_isolated: str
    midground_main: str
    background_plate: str

class DocumentAsset(BaseModel):
    source_url: str
    page: Optional[int] = None
    highlight_text: str

class AudioCue(BaseModel):
    sfx_category: Literal["WHOOSH", "SUB_BASS_HIT", "TENSION_RISER", "MECHANICAL_FOLEY",
                          "PAPER_SLIDE", "GLITCH", "AMBIENT_ROOM"]
    trigger_word: str
    volume_db: float = -8.0
    sfx_generation_prompt: str

class SceneItem(BaseModel):
    scene_id: str = Field(pattern=r"^S\d{3}$")
    act_number: int = Field(ge=1, le=5)
    narrative_phase: Phase
    visual_mode: VisualMode
    voiceover_text: str
    pause_after_sec: float = Field(ge=0.1, le=1.0, default=0.3)
    flux_base_image_prompt: str
    negative_prompt: Optional[str] = None
    reference_entities: List[str] = []
    video_motion_prompt: Optional[str] = None
    camera_move: Optional[Literal["SLOW_PUSH_IN", "HANDHELD_TENSION", "ORBIT_3D", "PULL_BACK", "STATIC"]] = None
    parallax_spec: Optional[ParallaxLayers] = None
    document_asset: Optional[DocumentAsset] = None
    on_screen_text: Optional[str] = None          # được dùng chữ số
    visual_bridge_from_prev: str
    audio_cues: List[AudioCue] = Field(min_length=1, max_length=3)
    evidence_refs: List[str] = []
    # Điền bởi N8, không do LLM viết:
    start_sec: float = 0.0
    duration_sec: float = 0.0
    duration_source: Literal["estimated", "tts_actual"] = "estimated"
    video_duration_sec: Optional[float] = None

    @model_validator(mode="after")
    def enforce_quality(self) -> "SceneItem":
        vo = self.voiceover_text
        n_words = len(vo.split())
        if not 8 <= n_words <= 24:
            raise ValueError(f"[{self.scene_id}] voiceover {n_words} từ, cần 8–24.")
        if re.search(r"\d", vo):
            raise ValueError(f"[{self.scene_id}] voiceover chứa chữ số; viết bằng chữ (số hiển thị đưa vào on_screen_text).")
        low = vo.lower()
        for p in BANNED_AI_PHRASES:
            if p in low:
                raise ValueError(f"[{self.scene_id}] cụm cấm '{p}'.")
        words = set(re.findall(r"[a-z']+", low))
        for c in self.audio_cues:
            if re.sub(r"[^a-z']", "", c.trigger_word.lower()) not in words:
                raise ValueError(f"[{self.scene_id}] trigger_word '{c.trigger_word}' không có trong voiceover.")
        if len(self.flux_base_image_prompt.split()) < 40:
            raise ValueError(f"[{self.scene_id}] flux prompt < 40 từ.")
        if self.narrative_phase == "HOOK" and self.visual_mode != "AI_VIDEO":
            raise ValueError(f"[{self.scene_id}] cảnh HOOK phải là AI_VIDEO.")
        m = self.visual_mode
        if m == "AI_VIDEO" and not (self.video_motion_prompt and self.camera_move):
            raise ValueError(f"[{self.scene_id}] AI_VIDEO cần video_motion_prompt và camera_move.")
        if m == "STATIC_PARALLAX" and not self.parallax_spec:
            raise ValueError(f"[{self.scene_id}] STATIC_PARALLAX cần parallax_spec.")
        if m == "DOCUMENT_HIGHLIGHT" and not self.document_asset:
            raise ValueError(f"[{self.scene_id}] DOCUMENT_HIGHLIGHT cần document_asset (tài liệu thật).")
        if m == "KINETIC_DATA_CARD" and not self.on_screen_text:
            raise ValueError(f"[{self.scene_id}] KINETIC_DATA_CARD cần on_screen_text.")
        return self

class ActScenes(BaseModel):
    scenes: List[SceneItem]

class MasterScript(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    source_rival_url: str
    plan: MasterPlan
    scenes: List[SceneItem]
    disclosure_ai_generated: bool = True
    estimated_total_duration_sec: float = 0.0
```

---

## 6. CODE LÕI ĐÃ SỬA (`core/graph.py`)

Khác v3.0: Hunter gọi công cụ thật; FSS/dừng/định tuyến do code; có Verifier; Node 7 có vòng retry theo cảnh; Human Gate; checkpointer; không dùng hack `__bases__`.

```python
import operator, time
from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send, interrupt
from langgraph.checkpoint.sqlite import SqliteSaver   # prod: PostgresSaver
from pydantic import ValidationError

from core.schemas import *
from core.llm import llm        # llm("architect"|"hunter"|"prosecutor"|"writer"|"autopsy") theo models.yaml
from core.config import RUN_BUDGET
from tools.forensic_search import search_and_scrape     # Exa/Tavily -> Firecrawl -> [{url, markdown}]
from tools.verify import verify_evidence, classify_tier, dedupe_facts
from tools.scoring import compute_fss, new_unique_facts
from tools.assemble import assemble_package
from tools.youtube_autopsy import node_n1_autopsy as n1_autopsy

class BrainState(TypedDict):
    run_id: str
    youtube_url: str
    rival_transcript: str
    rival_comments: List[str]
    autopsy: RivalAutopsyReport
    hypotheses: List[CounterHypothesis]
    vault: Annotated[List[EvidenceItem], operator.add]      # gộp kết quả song song
    indictments: Annotated[List[ProsecutorIndictment], operator.add]
    round: int
    new_facts_history: List[int]
    spent_usd: float
    started_at: float
    fss: float
    exit_reason: str
    quality_passed: bool
    approved_hypothesis_id: str
    plan: MasterPlan
    scenes: List[SceneItem]

class HunterTask(TypedDict):
    hypothesis_id: str
    queries: List[str]
    engine: str

# ---------------- N2 ----------------
def n2_architect(state: BrainState):
    last = state["indictments"][-1] if state.get("indictments") else None
    rejected = last.reasoning if last and last.verdict == "DISCARD_AND_RETHINK" else ""
    a = state["autopsy"]
    out = llm("architect").with_structured_output(HypothesisBatch).invoke(
        f"Rival thesis: {a.rival_core_thesis}\nWeak claims: {a.superficial_claims}\n"
        f"Audience questions: {a.audience_unanswered_questions}\nPreviously rejected because: {rejected}\n"
        "Propose 3 counter-hypotheses. Each must name a smoking-gun evidence type that is "
        "realistically findable online (court docs, official reports, archives, papers).")
    return {"hypotheses": out.hypotheses}

def fan_out_hunters(state: BrainState):
    return [Send("n3_hunter", {"hypothesis_id": h.hypothesis_id,
                               "queries": h.initial_search_vectors, "engine": "AUTO"})
            for h in state["hypotheses"]]

# ---------------- N3 (công cụ thật) + N3b Verifier ----------------
def n3_hunter(task: HunterTask):
    pages = search_and_scrape(task["queries"], engine=task["engine"], max_pages=6)  # [{url, markdown}]
    if not pages:
        return {"vault": []}
    corpus = "\n\n".join(f"### SOURCE: {p['url']}\n{p['markdown'][:12000]}" for p in pages)
    batch = llm("hunter").with_structured_output(HarvestBatch).invoke(
        "Extract facts ONLY from the SOURCE texts below. Never use outside knowledge. "
        "Every item needs source_url and a verbatim_quote copied exactly from that source. "
        f"Hypothesis: {task['hypothesis_id']}\n\n{corpus}")
    page_map = {p["url"]: p["markdown"] for p in pages}
    clean = []
    for e in batch.new_evidence:
        if verify_evidence(e, page_map):           # URL thuộc pages + quote là chuỗi con
            e.source_tier = classify_tier(e.source_url)
            e.verified = True
            clean.append(e)
    return {"vault": clean}

# ---------------- N3c Scorer + N4 Prosecutor + Router ----------------
def n4_prosecutor(state: BrainState):
    vault = dedupe_facts(state["vault"])
    fss_pre = compute_fss(vault, contradictions=0)
    ind = llm("prosecutor").with_structured_output(ProsecutorIndictment).invoke(
        "You are a red-team prosecutor. List flaws and targeted search directives. "
        "Do NOT output any score. Tests: primary source, forensic chronology, tangible visual artifact, "
        f"differentiation vs rival.\nHypotheses: {state['hypotheses']}\n"
        f"Verified evidence ({len(vault)}): {[e.model_dump() for e in vault]}\nCurrent FSS (code): {fss_pre:.2f}")
    fss = compute_fss(vault, contradictions=ind.unexplained_contradictions)
    hist = state.get("new_facts_history", []) + [new_unique_facts(state["vault"], vault)]
    rnd = state.get("round", 0) + 1

    passed = fss >= 0.75 and any(e.source_tier in ("PRIMARY", "ACADEMIC") for e in vault)
    over_budget = (state.get("spent_usd", 0) > RUN_BUDGET["max_usd"] or
                   (time.time() - state["started_at"]) / 60 > RUN_BUDGET["max_minutes"])
    saturated = len(hist) >= 2 and hist[-1] < 3 and hist[-2] < 3
    if passed:                                   reason = "PASSED"
    elif over_budget:                            reason = "BUDGET"
    elif saturated:                              reason = "SATURATED"
    elif rnd >= 4:                               reason = "MAX_ROUNDS"
    elif ind.verdict == "DISCARD_AND_RETHINK":   reason = "RETHINK"
    else:                                        reason = "CONTINUE"
    return {"indictments": [ind], "fss": fss, "round": rnd, "new_facts_history": hist,
            "exit_reason": reason, "quality_passed": passed,
            "approved_hypothesis_id": ind.winning_hypothesis_id}

def route_after_prosecutor(state: BrainState):
    r = state["exit_reason"]
    if r == "RETHINK":
        return "n2_architect"
    if r == "CONTINUE":
        flaws = state["indictments"][-1].identified_flaws
        return [Send("n3_hunter", {"hypothesis_id": state["approved_hypothesis_id"],
                                   "queries": [f.targeted_search_directive for f in flaws],
                                   "engine": "DEEP"})]
    return "n5_human_gate"

# ---------------- N5 Human Gate ----------------
def n5_human_gate(state: BrainState):
    decision = interrupt({
        "winning_hypothesis": state["approved_hypothesis_id"],
        "fss": state["fss"], "exit_reason": state["exit_reason"],
        "quality_passed": state["quality_passed"],
        "evidence_count": len(state["vault"]),
        "unresolved": [f.critique_detail for f in state["indictments"][-1].identified_flaws],
    })   # UI trả {"approve": bool, "hypothesis_id": "..."}
    if not decision.get("approve"):
        return {"exit_reason": "RETHINK"}
    return {"approved_hypothesis_id": decision.get("hypothesis_id", state["approved_hypothesis_id"])}

def route_after_gate(state: BrainState):
    return "n2_architect" if state["exit_reason"] == "RETHINK" else "n6a_plan"

# ---------------- N6a / N6b / N7 ----------------
def n6a_plan(state: BrainState):
    vault = dedupe_facts(state["vault"])
    plan = llm("writer").with_structured_output(MasterPlan).invoke(
        "Design a 5-act documentary plan + StyleBible with >=3 entity locks (CHAR_/OBJ_/LOC_), each with "
        "reference_image_prompt. Use ONLY these verified facts. Put unanswered questions in unresolved_hooks.\n"
        f"Hypothesis: {state['approved_hypothesis_id']}\nFacts: {[e.model_dump() for e in vault]}")
    return {"plan": plan}

def _write_batch(act, plan, vault, prev_bridge, first_id, count) -> List[SceneItem]:
    """N6b + N7: sinh lô <=12 cảnh dưới dạng JSON thô, validate từng cảnh bằng Pydantic;
    cảnh lỗi chỉ được sinh lại riêng (tối đa 3 lần)."""
    gen = llm("writer").with_structured_output(dict)     # trả JSON thô, KHÔNG validate hộ
    good: dict[str, SceneItem] = {}
    errors: dict[str, str] = {}
    target_ids = [f"S{first_id + i:03d}" for i in range(count)]
    for attempt in range(3):
        todo = [i for i in target_ids if i not in good]
        if not todo:
            break
        raw = gen.invoke(
            f"Write scenes {todo} for Act {act.act_number} '{act.act_title}' ({act.narrative_phase}). "
            f"Beats: {act.story_beats}. Continue from: {prev_bridge}. Act ends with: {act.open_loop_cliffhanger}. "
            f"StyleBible: {plan.style_bible.model_dump_json()}. "
            f"Evidence (cite evidence_refs by id): {[e.model_dump() for e in vault]}. "
            f"Fix previous errors per scene: {errors}. Return {{'scenes': [...]}}")
        for item in raw.get("scenes", []):
            try:
                sc = SceneItem.model_validate(item)
                if set(sc.evidence_refs) - {e.evidence_id for e in vault}:
                    raise ValueError("evidence_refs không tồn tại trong dossier")
                good[sc.scene_id] = sc
                errors.pop(sc.scene_id, None)
            except (ValidationError, ValueError) as ex:
                errors[item.get("scene_id", "?")] = str(ex)[:300]
    # Cảnh vẫn lỗi sau 3 lần: ghi vào quality_report.needs_human_fix, không làm sập run
    return [good[i] for i in target_ids if i in good]

def n6b_write_all(state: BrainState):
    vault = dedupe_facts(state["vault"]); plan = state["plan"]
    scenes, prev, nid = [], "COLD OPEN inside a physical room at the moment of failure.", 1
    for act in plan.acts:
        remaining = act.target_scene_count
        while remaining > 0:
            n = min(12, remaining)
            batch = _write_batch(act, plan, vault, prev, nid, n)
            scenes += batch; nid += n; remaining -= n
            if batch:
                prev = f"{batch[-1].voiceover_text} | {batch[-1].flux_base_image_prompt}"
    return {"scenes": scenes}

# ---------------- N8 Assembler ----------------
def n8_assemble(state: BrainState):
    assemble_package(state)   # start_sec/duration, kiểm ngân sách theo thời lượng, ghi production_package/
    return {}

def build_graph(db_path="brain.sqlite"):
    g = StateGraph(BrainState)
    for name, fn in [("n1_autopsy", n1_autopsy), ("n2_architect", n2_architect),
                     ("n3_hunter", n3_hunter), ("n4_prosecutor", n4_prosecutor),
                     ("n5_human_gate", n5_human_gate), ("n6a_plan", n6a_plan),
                     ("n6b_write", n6b_write_all), ("n8_assemble", n8_assemble)]:
        g.add_node(name, fn)
    g.add_edge(START, "n1_autopsy")
    g.add_edge("n1_autopsy", "n2_architect")
    g.add_conditional_edges("n2_architect", fan_out_hunters, ["n3_hunter"])
    g.add_edge("n3_hunter", "n4_prosecutor")
    g.add_conditional_edges("n4_prosecutor", route_after_prosecutor,
                            ["n2_architect", "n3_hunter", "n5_human_gate"])
    g.add_conditional_edges("n5_human_gate", route_after_gate, ["n2_architect", "n6a_plan"])
    g.add_edge("n6a_plan", "n6b_write")
    g.add_edge("n6b_write", "n8_assemble")
    g.add_edge("n8_assemble", END)
    return g.compile(checkpointer=SqliteSaver.from_conn_string(db_path))
```

> [!WARNING]
> Đây là khung đúng cấu trúc, **chưa chạy thử**. Cần viết `n1_autopsy`, các file `tools/*`, `core/llm.py`, và kiểm tra API LangGraph theo phiên bản bạn cài (đặc biệt `with_structured_output(dict)` và cách `SqliteSaver` khởi tạo). `n3_hunter` chạy song song rồi đổ về `n4_prosecutor`; LangGraph chờ các worker cùng bước hoàn tất trước khi chạy N4.

---

## 7. LOGIC CÁC MODULE (`tools/`)

| File | Hàm | Việc làm |
|---|---|---|
| `youtube_autopsy.py` | `fetch_audio`, `transcribe`, `fetch_comments`, `node_n1_autopsy` | yt-dlp tải audio (hỗ trợ cookie/proxy), ffmpeg chuyển 16 kHz mono, Groq Whisper có word timestamps → WPM & nhịp cắt; top 100 comment qua YouTube Data API. Transcript dài: chia đoạn, tóm tắt từng đoạn rồi gộp (không cắt cứng 30 000 ký tự). |
| `forensic_search.py` | `search_and_scrape` | Exa + Tavily → lọc URL trùng/SEO → Firecrawl/Jina cào Markdown; giới hạn `max_pages`; cache theo URL. |
| `verify.py` | `verify_evidence`, `classify_tier`, `dedupe_facts` | Quote ⊂ trang; tier theo domain/loại file; dedupe từng fact. |
| `scoring.py` | `compute_fss`, `new_unique_facts` | Công thức 3.1; chỉ đếm `verified=True`. |
| `assemble.py` | `assemble_package` | `duration_sec = words/WPM*60 + pause`, cộng dồn `start_sec`; kiểm ngân sách 3.3; sinh `asset_manifest`, `voiceover_full.txt`, `quality_report`, `package_manifest` (checksum); `MasterScript.model_validate` lần cuối. |

---

## 8. LỘ TRÌNH XÂY DỰNG (MVP) & TIÊU CHÍ HOÀN THÀNH

| Giai đoạn | Làm | Xong khi |
|---|---|---|
| **MVP-0** | Chốt **hợp đồng đầu ra** với Phase 2 (mục 1 + 5). Viết `schemas.py`, tạo 1 `master_script.json` mẫu tay, cho Phase 2 chạy thử. | Phase 2 đọc được file mẫu không cần sửa |
| **MVP-1** | N1 → N2 → N3 (+Verifier, Scorer), chưa có Prosecutor. Chạy 3 chủ đề. | ≥ 70% fact có quote xác minh; không fact bịa |
| **MVP-2** | Thêm N4, router, ngân sách, Human Gate, checkpointer. | Mỗi run dừng đúng `exit_reason`; chi phí < `max_usd` |
| **MVP-3** | N6a/N6b/N7 theo lô, N8 đóng gói. | Gói đầu ra qua `MasterScript` validate 100%; Phase 2 chạy end-to-end 1 video |
| **Hiệu chỉnh** | Chỉnh ngưỡng FSS, WPM, tỷ lệ chế độ hình ảnh sau 5 video thật. | Ghi trong `quality_report` |

### Kiểm thử
1. **Unit:** validator (chữ số, từ cấm, trigger_word), `compute_fss`, `verify_evidence` (quote giả phải bị loại), kiểm ngân sách Hybrid Motion.
2. **Contract test:** `production_package` mẫu → input Phase 2 → pass.
3. **Golden set:** 5 URL cố định, chạy lại sau mỗi lần đổi prompt/model; so FSS, chi phí, số cảnh phải retry.
4. **Chấm tay (1–5):** độ sâu bằng chứng, hook 60 giây, tính cụ thể hình ảnh, nhịp điệu, không "mùi AI".

---

## 9. RỦI RO CÒN LẠI
| Rủi ro | Giảm thiểu |
|---|---|
| YouTube chặn `yt-dlp` | Cookie/proxy; fallback: upload audio hoặc dán transcript |
| Không tìm được nguồn sơ cấp | `quality_passed=false` + Human Gate + `unresolved_hooks` |
| Chi phí vượt dự kiến | `RUN_BUDGET`, cache cào, model rẻ ở N1/N3 |
| Model đổi tên/ngừng | `models.yaml` tập trung; chạy golden set khi đổi |
| Nhân vật/đạo cụ lệch giữa các cảnh ở Phase 2 | `entity_locks` + sinh ảnh tham chiếu trước (có trong `asset_manifest`) |
| Model video giới hạn độ dài clip | `video_duration_sec ≤ 8`; N8 tự tách cảnh dài |

---

## 10. CẦN BẠN XÁC NHẬN ĐỂ KHÓA HỢP ĐỒNG
1. Ngôn ngữ lời bình: **tiếng Anh** (như tài liệu gốc) hay tiếng Việt? (Nếu Việt: đổi regex `[a-z']` trong validator và cách chuẩn hóa số.)
-> cái này tập trung cho tôi ngôn ngữ Anh,Tiếng Việt tôi sẽ đánh 2 thị trường này trước
2. Phase 2 dùng model nào cho ảnh/video/TTS? (quyết định độ dài prompt, `video_duration_sec`, tên trường.)
-> tôi cũng chưa xác định được đến phase tôi sẽ note ra tôi đang dự kiến sửa dụng những model miễn phí trước cái này bạn ưu tìm cho tôi những model miễn phí trước nhé
3. Tỷ lệ khung hình và FPS xuất (16:9, 30fps?).-> cái này tôi cũng chưa hiểu lắm 
4. Độ dài video mục tiêu (10/15/20 phút) → tổng số cảnh.-> cái này bạn tính giúp tôi
5. Ngân sách tối đa mỗi video (USD) để đặt `RUN_BUDGET`.-> 1$-1.5$ 

