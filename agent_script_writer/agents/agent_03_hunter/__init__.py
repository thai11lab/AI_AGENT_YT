"""Agent 03: Forensic Evidence Hunter — Truy lùng tài liệu gốc (Tavily / PubMed / .gov) & kiểm định trích dẫn nguyên văn."""
from core.orchestrator import run_single_hunter
from tools.forensic_search import search_and_scrape
from tools.verify import classify_tier, dedupe_facts, verify_evidence

__all__ = ["classify_tier", "dedupe_facts", "run_single_hunter", "search_and_scrape", "verify_evidence"]
