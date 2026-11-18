"""Tìm kiếm + lấy toàn văn trang. Ưu tiên Tavily (đã test OK) + Exa dự phòng + Jina Reader cào Markdown."""
import hashlib
import json
from pathlib import Path
from typing import Dict, List

import httpx

from core.config import ROOT, get_key

CACHE = ROOT / ".cache" / "search"
CACHE.mkdir(parents=True, exist_ok=True)
MAX_CHARS = 4000  # Cắt an toàn để không vượt giới hạn token TPM


def _cached(key: str, fn):
    p = CACHE / (hashlib.sha1(key.encode()).hexdigest() + ".json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    out = fn()
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def _tavily(query: str, n: int) -> List[Dict]:
    from tavily import TavilyClient
    key = get_key("TAVILY_API_KEY", required=False)
    if not key:
        return []
    client = TavilyClient(api_key=key)
    r = client.search(query, max_results=n, include_raw_content="markdown")
    return [
        {"url": x["url"], "markdown": (x.get("raw_content") or x.get("content") or "")[:MAX_CHARS]}
        for x in r.get("results", [])
    ]


def _exa(query: str, n: int) -> List[Dict]:
    key = get_key("EXA_API_KEY", required=False)
    if not key or key.startswith("tvly-"):  # tránh gọi nếu key rỗng hoặc nhầm
        return []
    from exa_py import Exa
    r = Exa(key).search_and_contents(
        query, num_results=n, type="auto", text={"max_characters": MAX_CHARS}
    )
    return [{"url": x.url, "markdown": x.text or ""} for x in r.results]


def search_and_scrape(queries: List[str], engine: str = "AUTO", max_pages: int = 4, per_query: int = 2) -> List[Dict]:
    """Trả về [{url, markdown}] đã bỏ trùng URL, tối đa max_pages bài."""
    seen: Dict[str, str] = {}

    for q in queries:
        if len(seen) >= max_pages:
            break
        results: List[Dict] = []

        # 1. Thử Tavily trước
        try:
            results += _cached("tav|" + q, lambda: _tavily(q, per_query))
        except Exception as e:
            print(f"[search] Tavily lỗi nhẹ cho '{q[:40]}': {e}")

        # 2. Thử Exa nếu chưa đủ kết quả
        if len(results) < per_query:
            try:
                results += _cached("exa|" + q, lambda: _exa(q, per_query))
            except Exception:
                pass

        for r in results:
            if r["url"] in seen or len(seen) >= max_pages:
                continue
            md = r.get("markdown", "")
            if len(md) >= 200:
                seen[r["url"]] = md[:MAX_CHARS]

    return [{"url": u, "markdown": m} for u, m in seen.items()]
