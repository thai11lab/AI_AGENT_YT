"""Agent 08: Self-Learning Human Voice & SQLite FTS5 Memory Engine."""
from .daily_trainer import (
    distill_transcript_with_llm,
    prune_and_optimize_memory_bank,
    run_daily_self_learning_cycle,
)
from .human_critic import (
    build_human_memory_prompt_block,
    evaluate_and_self_learn,
    infer_niche_tag,
    score_human_cadence,
)
from .memory_backend import SQLiteFTS5MemoryBackend
from .prosody_director import analyze_scene_prosody, inject_breathing_and_prosody_markers

__all__ = [
    "SQLiteFTS5MemoryBackend",
    "analyze_scene_prosody",
    "build_human_memory_prompt_block",
    "distill_transcript_with_llm",
    "evaluate_and_self_learn",
    "infer_niche_tag",
    "inject_breathing_and_prosody_markers",
    "prune_and_optimize_memory_bank",
    "run_daily_self_learning_cycle",
    "score_human_cadence",
]
