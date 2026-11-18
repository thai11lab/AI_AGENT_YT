"""Verifier (code thuần): chống bịa nguồn. LLM không được tự đánh dấu verified."""
import re
import unicodedata
from typing import Dict, List
from urllib.parse import urlparse

from core.schemas import EvidenceItem

MIN_QUOTE_CHARS = 20

PRIMARY_HINTS = (".gov", ".gov.vn", ".mil", "court", "uscourts.gov", "europa.eu", "un.org",
                 "sec.gov", "justice.gov", "legislation", "patents.google.com", "archives.gov")
ACADEMIC_HINTS = ("arxiv.org", "doi.org", ".edu", "nature.com", "science.org", "pubmed", "ncbi.nlm",
                  "sciencedirect.com", "springer.com", "jstor.org", "researchgate.net")
JOURNALISM_HINTS = ("reuters.com", "apnews.com", "bbc.", "nytimes.com", "theguardian.com", "wsj.com",
                    "bloomberg.com", "propublica.org", "washingtonpost.com", "ft.com", "vnexpress.net",
                    "tuoitre.vn", "thanhnien.vn", "cafef.vn")


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).casefold()
    t = t.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    t = re.sub(r"[\*_`#>\[\]\(\)]", " ", t)      # ký tự Markdown
    return re.sub(r"\s+", " ", t).strip()


def verify_evidence(e: EvidenceItem, page_map: Dict[str, str]) -> bool:
    """Hợp lệ khi URL nằm trong các trang vừa cào và trích dẫn là chuỗi con của trang đó."""
    page = page_map.get(e.source_url)
    if not page:
        return False
    quote = normalize(e.verbatim_quote)
    if len(quote) < MIN_QUOTE_CHARS:
        return False
    return quote in normalize(page)


def classify_tier(url: str) -> str:
    u = urlparse(url)
    host = (u.netloc or "").lower()
    full = (host + u.path).lower()
    if any(h in full for h in PRIMARY_HINTS):
        return "PRIMARY"
    if any(h in full for h in ACADEMIC_HINTS):
        return "ACADEMIC"
    if any(h in host for h in JOURNALISM_HINTS):
        return "JOURNALISM"
    return "SECONDARY"


def fact_key(e: EvidenceItem) -> str:
    return normalize(e.factual_claim)[:140]


def dedupe_facts(vault: List[EvidenceItem]) -> List[EvidenceItem]:
    """Bỏ fact trùng (cùng claim chuẩn hóa hoặc cùng trích dẫn). Giữ cái xuất hiện đầu tiên."""
    seen_claims, seen_quotes, out = set(), set(), []
    for e in vault:
        k, q = fact_key(e), normalize(e.verbatim_quote)
        if k in seen_claims or q in seen_quotes:
            continue
        seen_claims.add(k)
        seen_quotes.add(q)
        out.append(e)
    return out

