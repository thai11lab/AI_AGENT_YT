"""Shared Data Contracts between Phase 1 (production_package) and the 4 Phase 2 AI Agents."""
from pathlib import Path
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    word: str
    start_sec: float
    end_sec: float


class VoiceSceneOutput(BaseModel):
    scene_id: str
    audio_path: str
    duration_sec: float
    engine_used: str
    word_timings: List[WordTiming] = Field(default_factory=list)
    trigger_timestamps: Dict[str, float] = Field(default_factory=dict)


class VisualSceneOutput(BaseModel):
    scene_id: str
    visual_mode: str
    base_image_path: str
    fg_layer_path: Optional[str] = None
    bg_layer_path: Optional[str] = None
    provider_used: str = "local_cinema"


class MotionSceneOutput(BaseModel):
    scene_id: str
    video_clip_path: str
    duration_sec: float
    motion_engine: Literal[
        "cloud_ai_video",
        "local_25d_parallax",
        "document_anim",
        "kinetic_card_anim",
        "muse_video_api",
        "muse_lipsync_api",
        "local_musetalk",
        "audio_reactive_talking_head",
        "talking_head_fallback",
    ]
    camera_move: str = "SLOW_PUSH_IN"


class Phase2Manifest(BaseModel):
    run_id: str
    channel_id: str = "default_investigative_en"
    source_package_dir: str
    output_dir: str
    voice_outputs: Dict[str, VoiceSceneOutput] = Field(default_factory=dict)
    visual_outputs: Dict[str, VisualSceneOutput] = Field(default_factory=dict)
    motion_outputs: Dict[str, MotionSceneOutput] = Field(default_factory=dict)
    final_video_path: Optional[str] = None
    total_duration_sec: float = 0.0
