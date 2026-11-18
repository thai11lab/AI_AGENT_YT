"""Chấm điểm bằng code. Chỉ đếm bằng chứng đã xác minh (verified=True)."""
import re
from typing import List, Set

from core.schemas import EvidenceItem
from tools.verify import fact_key

PASS_THRESHOLD = 0.75


def _has_digit(s) -> bool:
    return bool(s and re.search(r"\d", s))


def compute_fss(vault: List[EvidenceItem], contradictions: int = 0) -> float:
    v = [e for e in vault if e.verified]
    c_pri = len({e.source_url for e in v if e.source_tier in ("PRIMARY", "ACADEMIC")})
    c_time = sum(1 for e in v if _has_digit(e.exact_timestamp_or_date))
    c_met = sum(1 for e in v if _has_digit(e.quantitative_metric))
    c_art = sum(1 for e in v if e.tangible_artifact_desc and e.tangible_artifact_desc.strip())
    score = 0.25 * (min(c_pri / 3, 1) + min(c_time / 8, 1) + min(c_met / 10, 1) + min(c_art / 8, 1))
    penalty = min(0.1 * contradictions, 0.5)
    return max(0.0, round(score - penalty, 4))


def passed(vault: List[EvidenceItem], contradictions: int = 0) -> bool:
    has_strong = any(e.verified and e.source_tier in ("PRIMARY", "ACADEMIC") for e in vault)
    return has_strong and compute_fss(vault, contradictions) >= PASS_THRESHOLD


def fact_keys(vault: List[EvidenceItem]) -> Set[str]:
    return {fact_key(e) for e in vault if e.verified}


def new_unique_facts(previous_keys: Set[str], vault: List[EvidenceItem]) -> int:
    """Số fact mới so với vòng trước (thay cho cosine). Lưu fact_keys(vault) vào state mỗi vòng."""
    return len(fact_keys(vault) - previous_keys)

