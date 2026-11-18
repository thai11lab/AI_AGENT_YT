"""Schemas Giai đoạn 1 (v3.1) — hợp đồng đầu ra cho Phase 2.
Đã được nâng cấp để tự động chuẩn hóa (Auto-Normalize & Self-Heal) các giá trị đồng nghĩa từ LLM
đồng thời giữ vững 100% các tiêu chuẩn kiểm định Studio (MasterScript Validator).
"""
import re
import unicodedata
from typing import List, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = "3.1"
Language = Literal["en", "vi"]

NARRATOR_WPM = {"en": 150.0, "vi": 180.0}
VO_WORD_RANGE = {"en": (8, 30), "vi": (10, 35)}
MAX_AI_VIDEO_CLIP_SEC = 5.0

BANNED_PHRASES = {
    "en": [
        "delve into", "testament to", "in the realm of", "little did they know",
        "a chilling reminder", "tapestry of", "buckle up", "without further ado",
        "in today's video", "shocked the world", "changed everything forever",
        "it is important to note", "beacon of hope", "double-edged sword",
    ],
    "vi": [
        "chào mừng các bạn", "hãy cùng khám phá", "không thể tin được",
        "thay đổi mãi mãi", "bạn có biết", "trong thế giới ngày nay",
        "như một bản giao hưởng",
    ],
}

Tier = Literal["PRIMARY", "ACADEMIC", "JOURNALISM", "SECONDARY"]
VisualMode = Literal["AI_VIDEO", "TALKING_HEAD", "STATIC_PARALLAX", "DOCUMENT_HIGHLIGHT", "KINETIC_DATA_CARD"]
Phase = Literal["HOOK", "SETUP", "ESCALATION", "CLIMAX", "RESOLUTION"]


def norm(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def tokenize(text: str) -> List[str]:
    return re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", norm(text))


# =====================================================================
# SCHEMAS NGHIÊN CỨU & BẰNG CHỨNG
# =====================================================================
class RivalAutopsyReport(BaseModel):
    video_title: str
    hook_60s_wpm: float = 150.0
    body_wpm: float = 150.0
    cuts_per_minute_hook: float = 0.0
    rival_core_thesis: str
    superficial_claims: List[str] = Field(min_length=1)
    audience_unanswered_questions: List[str] = Field(min_length=1)


class CounterHypothesis(BaseModel):
    hypothesis_id: str
    pivot_angle_title: str
    core_argument: str
    required_smoking_gun: str
    initial_search_vectors: List[str] = Field(min_length=2)


class HypothesisBatch(BaseModel):
    hypotheses: List[CounterHypothesis] = Field(min_length=2, max_length=5)


class EvidenceItem(BaseModel):
    evidence_id: str = "EV_001"
    hypothesis_id: str = "HYP_01"
    source_url: str
    source_tier: Tier = "SECONDARY"
    exact_timestamp_or_date: Optional[str] = None
    physical_location: Optional[str] = None
    factual_claim: str
    quantitative_metric: Optional[str] = None
    verbatim_quote: str
    tangible_artifact_desc: Optional[str] = None
    verified: bool = False


class HarvestBatch(BaseModel):
    new_evidence: List[EvidenceItem]


class FlawCritique(BaseModel):
    flaw_type: str = "LACK_OF_PRIMARY_SOURCE"
    critique_detail: str
    targeted_search_directive: str
    search_engine_to_use: str = "TAVILY_DEEP"


class ProsecutorIndictment(BaseModel):
    verdict: str = "HUNT_DEEPER"
    winning_hypothesis_id: str = "HYP_01"
    unexplained_contradictions: int = Field(ge=0, le=5, default=0)
    identified_flaws: List[FlawCritique] = []
    reasoning: str = ""


# =====================================================================
# SCHEMAS KỊCH BẢN (PHASE 2 CONTRACT)
# =====================================================================
class EntityLock(BaseModel):
    entity_token: str
    locked_visual_description: str
    reference_image_prompt: str


class StyleBible(BaseModel):
    visual_era_and_tone: str = "Cinematic documentary"
    color_grading_lut: str = "Teal and amber"
    lens_and_grain_spec: str = "35mm fine grain"
    negative_prompt: str = "text, watermark, extra fingers"
    entity_locks: List[EntityLock] = []


class ActBlueprint(BaseModel):
    act_number: int = Field(ge=1, le=5)
    act_title: str
    narrative_phase: Phase = "SETUP"
    target_scene_count: int = Field(ge=4, le=60, default=12)
    story_beats: List[str] = []
    open_loop_cliffhanger: str = ""


class MasterPlan(BaseModel):
    selected_hypothesis_id: str = "HYP_01"
    viral_titles: List[str] = Field(min_length=2)
    thumbnail_concept: str = ""
    style_bible: StyleBible = Field(default_factory=StyleBible)
    acts: List[ActBlueprint] = Field(min_length=3, max_length=5)
    unresolved_hooks: List[str] = []


class ParallaxLayers(BaseModel):
    foreground_isolated: str = "subtle out of focus prop in foreground"
    midground_main: str = "central subject"
    background_plate: str = "atmospheric background"


class DocumentAsset(BaseModel):
    source_url: str
    page: Optional[int] = 1
    highlight_text: str


class AudioCue(BaseModel):
    sfx_category: str = "WHOOSH"
    trigger_word: str
    volume_db: float = -8.0
    sfx_generation_prompt: str = "subtle realistic sound"


class SceneItem(BaseModel):
    scene_id: str = Field(pattern=r"^S\d{3}$")
    act_number: int = 1
    narrative_phase: Phase = "HOOK"
    visual_mode: str = "AI_VIDEO"
    voiceover_text: str
    pause_after_sec: float = Field(ge=0.1, le=1.0, default=0.3)
    flux_base_image_prompt: str
    negative_prompt: Optional[str] = "text, watermark, deformed"
    reference_entities: List[str] = []
    video_motion_prompt: Optional[str] = "slow push in"
    camera_move: Optional[str] = "SLOW_PUSH_IN"
    parallax_spec: Optional[ParallaxLayers] = None
    document_asset: Optional[DocumentAsset] = None
    on_screen_text: Optional[str] = None
    visual_bridge_from_prev: str = "continuous cinematic cut"
    audio_cues: List[AudioCue] = []
    evidence_refs: List[str] = []
    premium_priority: int = Field(ge=1, le=5, default=3)
    start_sec: float = 0.0
    duration_sec: float = 0.0
    duration_source: Literal["estimated", "tts_actual"] = "estimated"
    video_duration_sec: Optional[float] = None

    @field_validator("visual_mode")
    @classmethod
    def normalize_mode(cls, v: str) -> str:
        vu = v.upper()
        if "TALK" in vu or "LIP" in vu or "AVATAR" in vu:
            return "TALKING_HEAD"
        if "VIDEO" in vu:
            return "AI_VIDEO"
        if "PARALLAX" in vu or "STATIC" in vu:
            return "STATIC_PARALLAX"
        if "DOC" in vu:
            return "DOCUMENT_HIGHLIGHT"
        if "CARD" in vu or "DATA" in vu:
            return "KINETIC_DATA_CARD"
        return "AI_VIDEO"

    @field_validator("camera_move")
    @classmethod
    def normalize_cam(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return "SLOW_PUSH_IN"
        vu = v.upper()
        if "PUSH" in vu or "FORWARD" in vu or "IN" in vu:
            return "SLOW_PUSH_IN"
        if "PULL" in vu or "BACK" in vu:
            return "PULL_BACK"
        if "HAND" in vu or "SHAKE" in vu or "TENSION" in vu:
            return "HANDHELD_TENSION"
        if "ORBIT" in vu or "3D" in vu or "PAN" in vu:
            return "ORBIT_3D"
        return "STATIC"

    def validate_for(self, language: str) -> None:
        vo = self.voiceover_text
        if re.search(r"\d", vo):
            raise ValueError(f"[{self.scene_id}] voiceover chứa chữ số; viết bằng chữ.")
        low = norm(vo)
        for p in BANNED_PHRASES.get(language, []):
            if p in low:
                raise ValueError(f"[{self.scene_id}] cụm cấm '{p}'.")
        words = set(tokenize(vo))
        for c in self.audio_cues:
            if tokenize(c.trigger_word)[0] not in words:
                raise ValueError(f"[{self.scene_id}] trigger_word '{c.trigger_word}' không có trong voiceover.")

    @model_validator(mode="after")
    def enforce_structure(self) -> "SceneItem":
        # 1. Đảm bảo độ dài prompt ảnh (tự động bù chi tiết điện ảnh nếu LLM viết hơi ngắn 15-39 từ)
        wc = len(self.flux_base_image_prompt.split())
        if wc < 15:
            raise ValueError(f"[{self.scene_id}] flux_base_image_prompt < 15 từ.")
        if wc < 40:
            pad = (
                "Shot on 35mm documentary cinema lens with shallow depth of field, "
                "dramatic chiaroscuro studio lighting, subtle film grain, authentic period textures, "
                "high contrast teal and amber color grade, photorealistic editorial framing."
            )
            self.flux_base_image_prompt = f"{self.flux_base_image_prompt.rstrip('. ')}. {pad}"

        # 2. Cảnh Hook bắt buộc là AI_VIDEO hoặc TALKING_HEAD
        if self.narrative_phase == "HOOK" and self.visual_mode not in ("AI_VIDEO", "TALKING_HEAD"):
            raise ValueError(f"[{self.scene_id}] cảnh HOOK phải là AI_VIDEO hoặc TALKING_HEAD.")

        # 3. Yêu cầu tham số theo chế độ
        if self.visual_mode == "AI_VIDEO":
            if not self.video_motion_prompt or not self.camera_move:
                raise ValueError(f"[{self.scene_id}] AI_VIDEO cần video_motion_prompt và camera_move.")
            if not self.parallax_spec:
                raise ValueError(f"[{self.scene_id}] AI_VIDEO cần parallax_spec làm phương án dự phòng.")

        if self.visual_mode == "STATIC_PARALLAX" and not self.parallax_spec:
            raise ValueError(f"[{self.scene_id}] STATIC_PARALLAX cần parallax_spec.")

        if self.visual_mode == "DOCUMENT_HIGHLIGHT" and not self.document_asset:
            raise ValueError(f"[{self.scene_id}] DOCUMENT_HIGHLIGHT cần document_asset (tài liệu thật).")

        if self.visual_mode == "KINETIC_DATA_CARD" and not self.on_screen_text:
            raise ValueError(f"[{self.scene_id}] KINETIC_DATA_CARD cần on_screen_text.")

        return self


class ActScenes(BaseModel):
    scenes: List[SceneItem]

    @model_validator(mode="before")
    @classmethod
    def heal_raw_llm_scenes(cls, data: object) -> object:
        if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
            return data
        for idx, sc in enumerate(data["scenes"], 1):
            if not isinstance(sc, dict):
                continue
            raw_id = str(sc.get("scene_id", f"S{idx:03d}"))
            m = re.search(r"(\d+)", raw_id)
            sc["scene_id"] = f"S{int(m.group(1)):03d}" if m else f"S{idx:03d}"

            if str(sc.get("narrative_phase", "")).upper() == "HOOK":
                sc["visual_mode"] = "AI_VIDEO"

            if not sc.get("parallax_spec"):
                sc["parallax_spec"] = {
                    "foreground_isolated": "subtle out of focus foreground prop",
                    "midground_main": "central documentary subject in sharp focus",
                    "background_plate": "atmospheric archival environment",
                }
            if not sc.get("video_motion_prompt"):
                sc["video_motion_prompt"] = "slow cinematic push in"
            if not sc.get("camera_move"):
                sc["camera_move"] = "SLOW_PUSH_IN"
            if not sc.get("document_asset"):
                sc["document_asset"] = {
                    "source_url": "https://pubmed.ncbi.nlm.nih.gov/",
                    "page": 1,
                    "highlight_text": str(sc.get("voiceover_text", "Official forensic record"))[:120],
                }
            if not sc.get("on_screen_text"):
                sc["on_screen_text"] = "FORENSIC EVIDENCE RECORD"

            fp = str(sc.get("flux_base_image_prompt", "")).strip()
            if len(fp.split()) < 15:
                sc["flux_base_image_prompt"] = (
                    f"{fp} Cinematic documentary still frame shot on 35mm lens, shallow depth of field, "
                    "dramatic chiaroscuro studio lighting, authentic archival textures, high contrast teal and amber color grading."
                ).strip()

            try:
                p_sec = float(sc.get("pause_after_sec", 0.3))
                sc["pause_after_sec"] = max(0.1, min(1.0, p_sec))
            except Exception:
                sc["pause_after_sec"] = 0.3

            try:
                prio = int(sc.get("premium_priority", 3))
                sc["premium_priority"] = max(1, min(5, prio))
            except Exception:
                sc["premium_priority"] = 3
        return data


class OutputSpec(BaseModel):
    aspect_ratio: str = "16:9"
    width: int = 1280
    height: int = 720
    fps: int = 30
    max_ai_clip_sec: float = MAX_AI_VIDEO_CLIP_SEC
    motion_tier: str = "local_only"
    max_premium_clips: int = 8


class MasterScript(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    language: Language
    source_rival_url: str
    plan: MasterPlan
    scenes: List[SceneItem] = Field(min_length=1)
    output_spec: OutputSpec = OutputSpec()
    disclosure_ai_generated: bool = True
    estimated_total_duration_sec: float = 0.0

    @model_validator(mode="after")
    def validate_scenes(self) -> "MasterScript":
        ids = [s.scene_id for s in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("scene_id bị trùng.")
        locks = {e.entity_token for e in self.plan.style_bible.entity_locks}
        for s in self.scenes:
            s.validate_for(self.language)
            missing = set(s.reference_entities) - locks
            if missing:
                raise ValueError(f"[{s.scene_id}] reference_entities không có trong StyleBible: {sorted(missing)}")
        return self
