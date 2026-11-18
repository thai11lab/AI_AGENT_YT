"""Render plan: quyết định mỗi cảnh được render bằng cách nào theo motion_tier.

Đây là điểm duy nhất cần đổi để nâng cấp từ hướng 1 (local_only) lên hướng 2 (cloud_video):
Phase 1 và master_script.json KHÔNG đổi. Phase 2 chỉ cần:
  1. đặt output_spec.motion_tier = "cloud_video" (hoặc truyền tham số), và
  2. cắm một VideoBackend thật (xem Protocol bên dưới).
"""
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Protocol

from core.schemas import MasterScript, SceneItem

Renderer = Literal["PARALLAX_2_5D", "DOCUMENT_OVERLAY", "DATA_CARD", "VIDEO_I2V"]


@dataclass
class RenderTask:
    scene_id: str
    renderer: Renderer
    fallback: Optional[Renderer]       # dùng khi renderer chính lỗi/hết hạn mức; None = không có
    duration_sec: float


class VideoBackend(Protocol):
    """Hợp đồng cho backend video AI (hướng 2). Cài đặt sau: Wan/LTX cloud, Runway, Veo, ...
    Phải trả về đường dẫn file mp4 hoặc ném exception (Phase 2 sẽ tự rơi về fallback)."""

    def image_to_video(self, image_path: str, motion_prompt: str,
                       duration_sec: float, out_path: str) -> str: ...


def _base_renderer(s: SceneItem) -> Renderer:
    return {
        "STATIC_PARALLAX": "PARALLAX_2_5D",
        "AI_VIDEO": "PARALLAX_2_5D",           # mặc định local: ảnh + camera 2.5D
        "DOCUMENT_HIGHLIGHT": "DOCUMENT_OVERLAY",
        "KINETIC_DATA_CARD": "DATA_CARD",
    }[s.visual_mode]


def resolve_render_plan(script: MasterScript, motion_tier: Optional[str] = None) -> List[RenderTask]:
    tier = motion_tier or script.output_spec.motion_tier
    premium_ids = set()
    if tier == "cloud_video":
        cands = [s for s in script.scenes if s.visual_mode == "AI_VIDEO"]
        # ưu tiên cao nhất trước, hòa thì theo thứ tự xuất hiện (ổn định)
        cands.sort(key=lambda s: (-s.premium_priority, s.scene_id))
        premium_ids = {s.scene_id for s in cands[: script.output_spec.max_premium_clips]}
    plan: List[RenderTask] = []
    for s in script.scenes:
        if s.scene_id in premium_ids:
            plan.append(RenderTask(s.scene_id, "VIDEO_I2V", "PARALLAX_2_5D", s.duration_sec))
        else:
            plan.append(RenderTask(s.scene_id, _base_renderer(s), None, s.duration_sec))
    return plan


def summarize(plan: List[RenderTask]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for t in plan:
        out[t.renderer] = out.get(t.renderer, 0) + 1
    return out

