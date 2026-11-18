"""Agent 04: Red-Team Prosecutor — Công tố viên phản biện chéo và chấm điểm bằng chứng FSS (>= 0.75)."""
from core.orchestrator import run_node_4_prosecutor
from tools.scoring import compute_fss, fact_keys, new_unique_facts, passed

__all__ = ["compute_fss", "fact_keys", "new_unique_facts", "passed", "run_node_4_prosecutor"]
