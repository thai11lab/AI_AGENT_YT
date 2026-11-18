"""MVP-1: URL đối thủ -> autopsy -> 3 giả thuyết -> săn bằng chứng -> xác minh -> FSS.
Chưa có công tố viên/vòng lặp (MVP-2) và chưa viết kịch bản (MVP-3).

  python scripts/run_mvp1.py "<youtube_url>" [--transcript file.txt] [--lang en|vi]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import ROOT  # noqa: E402
from core.llm import structured  # noqa: E402
from core.schemas import RivalAutopsyReport, HypothesisBatch, HarvestBatch  # noqa: E402
from tools.forensic_search import search_and_scrape  # noqa: E402
from tools.scoring import compute_fss, passed  # noqa: E402
from tools.verify import verify_evidence, classify_tier, dedupe_facts  # noqa: E402
from tools.youtube_autopsy import build_input  # noqa: E402


def autopsy(video, lang):
    return structured("autopsy", f"""Analyze this competitor video (title: {video['title']}).
Return its core thesis, the claims that are superficial or unproven, and the questions viewers argue about in comments.
If there are no comments, infer likely unanswered questions from the transcript.
Set hook_60s_wpm={video.get('hook_60s_wpm', 0)}, body_wpm={video.get('body_wpm', 0)}, cuts_per_minute_hook=0.
Write in English.
TRANSCRIPT:
{video['transcript'][:60000]}
TOP COMMENTS:
{video['comments'][:100]}""", RivalAutopsyReport)


def architect(report):
    return structured("architect", f"""You are an investigative counter-narrative architect.
Rival thesis: {report.rival_core_thesis}
Weak claims: {report.superficial_claims}
Audience questions: {report.audience_unanswered_questions}
Propose exactly 3 counter-hypotheses (ids HYP_01..HYP_03). Each needs a smoking-gun evidence type that can
realistically be found online (court documents, official reports, archives, papers) and 3 specific web search queries.
""", HypothesisBatch, temperature=0.5)


def hunt(h, counter):
    pages = search_and_scrape(h.initial_search_vectors, max_pages=5)
    if not pages:
        return [], 0
    corpus = "\n\n".join(f"### SOURCE: {p['url']}\n{p['markdown'][:12000]}" for p in pages)
    batch = structured("hunter", f"""Extract facts ONLY from the SOURCE texts below. Never use outside knowledge.
Each item needs source_url (exactly as given) and verbatim_quote copied EXACTLY, character for character, from that source (at least 20 characters).
Prefer facts with exact dates/times, named people, measurements, and physical objects. Skip vague claims.
Hypothesis {h.hypothesis_id}: {h.pivot_angle_title} - {h.core_argument}
Smoking gun wanted: {h.required_smoking_gun}

{corpus}""", HarvestBatch)
    page_map = {p["url"]: p["markdown"] for p in pages}
    kept = []
    for e in batch.new_evidence:
        e.hypothesis_id = h.hypothesis_id
        if verify_evidence(e, page_map):
            e.source_tier = classify_tier(e.source_url)
            e.verified = True
            kept.append(e)
    return kept, len(batch.new_evidence)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--transcript")
    ap.add_argument("--lang", default="en")
    a = ap.parse_args()
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out = ROOT / "runs" / run_id
    out.mkdir(parents=True, exist_ok=True)

    print("[1/4] Lấy transcript...")
    video = build_input(a.url, a.transcript)
    print(f"      '{video['title']}' nguồn={video['source']} "
          f"{len(video['transcript'].split())} từ, {len(video['comments'])} comment")
    print("[2/4] Phân tích đối thủ...")
    report = autopsy(video, a.lang)
    print("      Luận điểm:", report.rival_core_thesis)
    print("[3/4] Lập giả thuyết...")
    hyps = architect(report).hypotheses
    for h in hyps:
        print(f"      {h.hypothesis_id}: {h.pivot_angle_title}")
    print("[4/4] Săn bằng chứng (song song)...")
    with ThreadPoolExecutor(3) as ex:
        results = list(ex.map(lambda h: hunt(h, report), hyps))

    summary = {}
    for h, (kept, total) in zip(hyps, results):
        kept = dedupe_facts(kept)
        for i, e in enumerate(kept, 1):
            e.evidence_id = f"EV_{h.hypothesis_id[-2:]}{i:02d}"
        summary[h.hypothesis_id] = {
            "title": h.pivot_angle_title, "extracted": total, "verified": len(kept),
            "fss": compute_fss(kept), "passed": passed(kept),
            "evidence": [e.model_dump() for e in kept]}
        print(f"      {h.hypothesis_id}: trích {total} -> xác minh {len(kept)} | FSS={summary[h.hypothesis_id]['fss']}")

    (out / "mvp1.json").write_text(json.dumps(
        {"video": {k: v for k, v in video.items() if k not in ("segments", "transcript")},
         "autopsy": report.model_dump(), "hypotheses": summary}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Kết quả:", out / "mvp1.json")


if __name__ == "__main__":
    main()

