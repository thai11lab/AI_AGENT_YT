"""Daily Curriculum & Self-Evolution Engine — Hệ thống Tự học & Làm giàu Kho Tri Thức Hàng Ngày cho Agent 08.
Cơ chế hoạt động 4 bước (Daily Knowledge Enrichment Pipeline):
1. Multi-Niche Breakout Harvest: Tự động lấy transcript từ các video triệu view / Outlier mới nổ (hoặc danh sách kênh bậc thầy như Lemmino, Fern, Veritasium, Kurzgesagt, Tifo Football).
2. LLM Masterclass Distiller (hoặc Heuristic Contrast Miner khi chạy offline): Bóc tách từng đoạn transcript thành cặp đối chiếu:
   - [❌ Câu tóm tắt kiểu đọc Slide vô hồn]
   - [✅ Câu kể chuyện người thật có chính kiến, nhịp dài-ngắn đan xen]
   - [💡 Quy tắc tâm lý học giữ chân người xem]
3. Bilingual Synthesis (EN + VI): Tự động chuyển hóa tinh hoa sang cả Tiếng Anh và Tiếng Việt tròn vành rõ chữ (18-32 từ, không chứa chữ số 0-9).
4. Ebbinghaus Memory Pruning & Reinforcement: Cộng điểm thưởng cho mẫu câu hiệu quả cao và tự động dọn dẹp các mẫu câu điểm thấp để bộ nhớ SQLite FTS5 luôn tinh gọn, sắc bén.
"""
import datetime
import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from agents.agent_08_self_learner.human_critic import infer_niche_tag, score_human_cadence
from agents.agent_08_self_learner.memory_backend import SQLiteFTS5MemoryBackend


class DistilledPatternItem(BaseModel):
    act_phase: str = Field(default="HOOK", description="HOOK | SETUP | ESCALATION | CLIMAX | RESOLUTION")
    persona_tone: str = Field(default="cold_forensic", description="cold_forensic | sarcastic_sharp | curious_explorer")
    topic_keywords: str = Field(description="5-8 keywords describing the narrative situation")
    bad_slide_text: str = Field(description="The boring, robotic, slide-reading version of this idea")
    human_gold_text: str = Field(
        description="The rich, opinionated, human storytelling version (16-28 words in target language, ZERO digits 0-9, complete sentences with long-short contrast)"
    )
    why_it_works: str = Field(description="1 concise rule explaining why this human cadence hooks the viewer")


class DistilledPatternBatch(BaseModel):
    patterns: List[DistilledPatternItem] = Field(default_factory=list)


# Danh sách các kênh/video mẫu bậc thầy theo từng ngách để Agent tự tuần tra hàng ngày
MASTER_CURRICULUM_QUERIES: Dict[str, List[str]] = {
    "football": [
        "tifo football tactical transfer mistake documentary",
        "hitc sevens football club collapse scandal",
    ],
    "netflix": [
        "villain ending explained hidden detail video essay",
        "nerdwriter1 scene breakdown cinematography",
    ],
    "gta": [
        "gta 5 mystery hidden secret solved documentary",
        "red dead redemption 2 strange man secret investigation",
    ],
    "general": [
        "lemmino mystery investigation documentary",
        "fern documentary crime investigation",
        "veritasium science paradox investigation",
    ],
}


def distill_transcript_with_llm(
    transcript: str,
    title: str,
    niche: str,
    language: str = "vi",
    brain: Optional[SQLiteFTS5MemoryBackend] = None,
) -> int:
    """Dùng LLM phân tích transcript triệu view để chưng cất ra các cặp [❌ Câu đọc Slide] vs [✅ Câu Người thật] nạp vào SQLite FTS5."""
    mem = brain or SQLiteFTS5MemoryBackend()
    clean_tx = (transcript or "").strip()[:7500]
    if len(clean_tx) < 150:
        return 0

    lang_desc = (
        "Vietnamese (Tiếng Việt tự nhiên, sắc sảo, tròn câu 18-32 từ, có từ nối đời thực như 'Trên giấy tờ...', 'Thế nhưng...', 'Nhìn kỹ vào...', tuyệt đối KHÔNG cụt ngủn)"
        if language == "vi"
        else "English (Razor-sharp investigative storytelling, 15-26 words per pattern, complete sentences with stance markers like 'On paper...', 'In reality?', 'Wait—look closer at...')"
    )

    prompt = f"""You are the Head Story Editor training an elite YouTube Scriptwriting AI.
Analyze this viral video transcript (Title: '{title}', Niche: '{niche}').
Extract 3 of the sharpest, most engaging storytelling moments and convert them into contrast training pairs in {lang_desc}.

MANDATORY RULES FOR EACH PATTERN:
1. bad_slide_text: Write how a boring, robotic AI would summarize that point like a PowerPoint slide.
2. human_gold_text: Write the rich, opinionated, human narrator version in {lang_desc}.
   - MUST be 18 to 32 words (if Vietnamese) or 15 to 26 words (if English).
   - MUST contain 1-2 complete, flowing spoken sentences (full Subject - Verb - Context) paired with a sharp human stance or twist.
   - NEVER write choppy telegraphic fragments!
   - ZERO digits (0-9): spell out all numbers in spoken words.
3. why_it_works: Explain the exact psychological or rhythmic trick used.

TRANSCRIPT EXCERPT:
{clean_tx}
"""
    added = 0
    try:
        from core.llm import structured

        batch = structured("writer", prompt, DistilledPatternBatch, temperature=0.35)
        for p in batch.patterns[:4]:
            gold = p.human_gold_text.strip()
            if re.search(r"\d", gold) or len(gold.split()) < 14:
                continue
            sc = score_human_cadence([gold])["human_score"]
            row_id = mem.add_memory(
                memory_type="GOLDEN",
                niche=niche,
                act_phase=p.act_phase.upper(),
                persona_tone=p.persona_tone,
                topic_keywords=p.topic_keywords,
                bad_slide_text=p.bad_slide_text,
                human_gold_text=gold,
                why_it_works=f"[Daily Distiller - {title[:30]}] {p.why_it_works}",
                burstiness_score=max(8.8, sc),
                win_score=26.0,
            )
            if row_id > 0:
                added += 1
    except Exception:
        # Fallback về bộ đào Heuristic nếu không gọi mạng/LLM
        added = mem.learn_from_competitor_transcript(clean_tx, niche=niche, source_title=title)

    return added


def prune_and_optimize_memory_bank(
    brain: Optional[SQLiteFTS5MemoryBackend] = None,
    max_entries_per_niche: int = 250,
) -> Dict[str, int]:
    """Dọn dẹp các mẫu câu kém chất lượng/cụt ngủn và giới hạn dung lượng tinh hoa cho mỗi ngách."""
    mem = brain or SQLiteFTS5MemoryBackend()
    removed = 0
    with mem._connect() as conn:
        # 1. Xóa các bản ghi tự học bị ngắn cụt (< 85 ký tự) nhưng giữ tuyệt đối USER_FIX
        cur = conn.execute(
            "DELETE FROM memory_entries WHERE memory_type != 'USER_FIX' AND length(human_gold_text) < 85"
        )
        removed += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

        # 2. Giữ lại top max_entries_per_niche có win_score cao nhất cho mỗi ngách
        niches = [r[0] for r in conn.execute("SELECT DISTINCT niche FROM memory_entries").fetchall()]
        for n in niches:
            cur2 = conn.execute(
                """
                DELETE FROM memory_entries
                WHERE niche = ?
                  AND memory_type != 'USER_FIX'
                  AND id NOT IN (
                      SELECT id FROM memory_entries
                      WHERE niche = ?
                      ORDER BY win_score DESC, burstiness_score DESC, id DESC
                      LIMIT ?
                  )
                """,
                (n, n, max_entries_per_niche),
            )
            removed += cur2.rowcount if cur2.rowcount and cur2.rowcount > 0 else 0
        conn.commit()

    st = mem.stats()
    return {"pruned_entries": removed, **st}


def run_daily_self_learning_cycle(
    niche: str = "all",
    languages: Optional[List[str]] = None,
    max_videos: int = 2,
    custom_urls: Optional[List[str]] = None,
    use_llm_distiller: bool = True,
    brain: Optional[SQLiteFTS5MemoryBackend] = None,
) -> Dict:
    """Chạy 1 chu kỳ Tự học Hàng ngày: Quét video triệu view mới nổ -> Bóc băng -> Chưng cất mẫu câu EN/VI -> Tối ưu FTS5 DB."""
    from tools.niche_radar import scan_breakout_niches
    from tools.youtube_autopsy import build_input

    mem = brain or SQLiteFTS5MemoryBackend()
    langs = languages or ["vi", "en"]
    urls_to_learn: List[Dict[str, str]] = []

    if custom_urls:
        for u in custom_urls:
            if u.strip():
                urls_to_learn.append({"url": u.strip(), "niche": "general" if niche == "all" else niche})
    else:
        # Kết nối với Agent 00 (Niche Radar) để lấy các video Outlier mới nổ ngoài đời thực
        radar_hits = scan_breakout_niches(live_youtube_scan=True)
        for hit in radar_hits:
            vid = hit.get("selected_video") or {}
            v_url = vid.get("url", "")
            if not v_url:
                continue
            h_niche = infer_niche_tag(f"{hit.get('niche_name', '')} {vid.get('title', '')}")
            if niche != "all" and h_niche != niche:
                continue
            if not any(x["url"] == v_url for x in urls_to_learn):
                urls_to_learn.append({"url": v_url, "niche": h_niche})
            if len(urls_to_learn) >= max_videos:
                break

    total_learned = 0
    processed_videos = []

    for item in urls_to_learn[:max_videos]:
        u = item["url"]
        try:
            v_data = build_input(u)
            tx = v_data.get("transcript", "")
            title = v_data.get("title", "Viral Video")
            n_tag = infer_niche_tag(f"{title} {tx[:600]}") if item["niche"] == "general" else item["niche"]

            learned_this_vid = 0
            if use_llm_distiller:
                for lg in langs:
                    learned_this_vid += distill_transcript_with_llm(
                        transcript=tx,
                        title=title,
                        niche=n_tag,
                        language=lg,
                        brain=mem,
                    )
            else:
                learned_this_vid += mem.learn_from_competitor_transcript(tx, niche=n_tag, source_title=title)

            total_learned += learned_this_vid
            processed_videos.append({"url": u, "title": title, "niche": n_tag, "patterns_learned": learned_this_vid})
        except Exception as e:
            processed_videos.append({"url": u, "error": str(e)[:120], "patterns_learned": 0})

    prune_stats = prune_and_optimize_memory_bank(brain=mem)
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "videos_processed": processed_videos,
        "new_patterns_learned": total_learned,
        "memory_bank_stats": prune_stats,
    }
