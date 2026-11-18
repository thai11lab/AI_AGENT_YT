"""Bộ điều phối toàn bộ đồ thị tự phản biện Giai đoạn 1 (N1 -> N8).
Thực thi 100% logic vòng lặp, kiểm định nguồn, tự phản biện và tự sửa kịch bản theo Plan v3.1.
Được tinh chỉnh kích thước ngữ cảnh để chạy mượt mà trên cả Gemini và Groq Free Tier.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.config import ROOT, RUN_BUDGET
from core.llm import structured, text
from core.schemas import (
    ActBlueprint,
    ActScenes,
    CounterHypothesis,
    EvidenceItem,
    HarvestBatch,
    HypothesisBatch,
    MasterPlan,
    MasterScript,
    ProsecutorIndictment,
    RivalAutopsyReport,
    SceneItem,
)
from tools.assemble import assemble_package
from tools.forensic_search import search_and_scrape
from tools.scoring import compute_fss, fact_keys, new_unique_facts, passed
from tools.verify import classify_tier, dedupe_facts, verify_evidence
from tools.youtube_autopsy import build_input


# =====================================================================
# NODE 1: AUTOPSY ĐỐI THỦ
# =====================================================================
def run_node_1_autopsy(video_data: Dict, language: str) -> RivalAutopsyReport:
    # Cắt gọn transcript 15.000 ký tự để vừa vặn trong token quota của mọi provider
    transcript_clean = video_data.get('transcript', '')[:15000]
    try:
        from agents.agent_08_self_learner import SQLiteFTS5MemoryBackend, infer_niche_tag

        brain = SQLiteFTS5MemoryBackend()
        n_tag = infer_niche_tag(str(video_data.get("title", "")) + " " + transcript_clean[:600])
        learned_cnt = brain.learn_from_competitor_transcript(transcript_clean, niche=n_tag, source_title=str(video_data.get("title", "")))
        if learned_cnt > 0:
            print(f"  [Self-Learner] Đã tự học {learned_cnt} mẫu nhịp câu người thật từ video đối thủ vào SQLite FTS5 ({n_tag}).", flush=True)
    except Exception:
        pass
    prompt = f"""You are a Master Investigative Story Analyst.
Analyze this competitor video (Title: {video_data.get('title', 'Unknown')}).
Identify:
1. rival_core_thesis: The main message or argument they are presenting.
2. superficial_claims: At least 3 claims made with weak evidence, lazy assumptions, or clichés.
3. audience_unanswered_questions: At least 3 major questions, doubts, or gaps that viewers would naturally ask or argue about.
(If comments are empty, deduce the top 3 gaps from the transcript itself).

WPM stats: hook_60s_wpm={video_data.get('hook_60s_wpm', 150.0)}, body_wpm={video_data.get('body_wpm', 150.0)}, cuts_per_minute_hook=0.

TRANSCRIPT:
{transcript_clean}
"""
    return structured("autopsy", prompt, RivalAutopsyReport)


# =====================================================================
# NODE 2: KIẾN TRÚC SƯ GIẢ THUYẾT (COUNTER-HYPOTHESES)
# =====================================================================
def run_node_2_architect(
    autopsy_report: RivalAutopsyReport,
    past_rejections: str = ""
) -> List[CounterHypothesis]:
    prompt = f"""You are a Counter-Narrative Architect for an elite documentary studio.
Competitor Thesis: {autopsy_report.rival_core_thesis}
Competitor Blindspots: {autopsy_report.superficial_claims}
Audience Questions: {autopsy_report.audience_unanswered_questions}
{f'NOTE PREVIOUS CRITIQUE FROM PROSECUTOR: {past_rejections}' if past_rejections else ''}

Propose exactly 3 radical, fact-driven Counter-Hypotheses (ids HYP_01, HYP_02, HYP_03).
For each hypothesis:
- pivot_angle_title: Catchy forensic angle.
- core_argument: Why the conventional story is wrong, incomplete, or a cover-up.
- required_smoking_gun: The exact primary record needed (court docket, declassified log, financial wire, technical spec, autopsy).
- initial_search_vectors: Exactly 3 highly specific web queries (using site:, filetype:pdf, names, serials).
"""
    batch = structured("architect", prompt, HypothesisBatch, temperature=0.4)
    return batch.hypotheses


# =====================================================================
# NODE 3: THỢ SĂN BẰNG CHỨNG (HUNT & VERIFY)
# =====================================================================
def run_single_hunter(hyp: CounterHypothesis, queries: List[str]) -> List[EvidenceItem]:
    pages = search_and_scrape(queries, max_pages=3, per_query=2)
    if not pages:
        return []

    # Mỗi trang lấy tối đa 2.500 ký tự để tổng ngữ cảnh luôn dưới 3.500 tokens
    corpus = "\n\n".join(f"### SOURCE: {p['url']}\n{p['markdown'][:2500]}" for p in pages)
    prompt = f"""Extract hard, forensic facts ONLY from the SOURCE texts below. NEVER use outside knowledge.
For each fact:
- source_url: EXACT URL from the header.
- verbatim_quote: MUST be a verbatim string (>= 20 characters) copied EXACTLY from that source.
- factual_claim: Specific factual assertion.
- exact_timestamp_or_date: Specific time/date if mentioned, else null.
- physical_location: Specific physical location if mentioned, else null.
- quantitative_metric: Dollars, serial numbers, temperatures, codes if mentioned, else null.
- tangible_artifact_desc: Concrete physical object/prop details for art generation, else null.

Hypothesis {hyp.hypothesis_id}: {hyp.pivot_angle_title} - {hyp.core_argument}
Smoking gun sought: {hyp.required_smoking_gun}

{corpus}
"""
    batch = structured("hunter", prompt, HarvestBatch)
    page_map = {p["url"]: p["markdown"] for p in pages}
    verified = []
    for item in batch.new_evidence:
        item.hypothesis_id = hyp.hypothesis_id
        if verify_evidence(item, page_map):
            item.source_tier = classify_tier(item.source_url)
            item.verified = True
            verified.append(item)
    return verified


# =====================================================================
# NODE 4: CÔNG TỐ VIÊN PHẢN BIỆN (RED-TEAM PROSECUTOR)
# =====================================================================
def run_node_4_prosecutor(
    hypotheses: List[CounterHypothesis],
    vault: List[EvidenceItem],
    round_num: int,
    current_fss: float
) -> ProsecutorIndictment:
    evidence_summary = [
        {
            "id": e.evidence_id,
            "hyp": e.hypothesis_id,
            "tier": e.source_tier,
            "claim": e.factual_claim,
            "metric": e.quantitative_metric,
            "time": e.exact_timestamp_or_date,
            "quote": e.verbatim_quote[:80] + "..."
        }
        for e in vault[:15]  # Tối đa 15 bằng chứng hàng đầu để prompt ngắn gọn
    ]

    prompt = f"""You are the Ruthless Red-Team Investigative Prosecutor.
Interrogate the evidence collected against our candidate hypotheses.
Round: {round_num} | Current FSS Score: {current_fss:.2f}

Candidate Hypotheses:
{[h.model_dump() for h in hypotheses]}

Evidence Vault ({len(evidence_summary)} items):
{json.dumps(evidence_summary, indent=2, ensure_ascii=False)}

RUTHLESS EVALUATION CRITERIA:
1. Nguồn sơ cấp: Có biên bản, tài liệu kỹ thuật, báo cáo chính thức không?
2. Mốc thời gian: Có giờ/phút hoặc ngày cụ thể không? Có mâu thuẫn thời gian không?
3. Hiện vật vật lý: Có đủ chi tiết vật thể để AI vẽ ảnh không?
4. Khác biệt với đối thủ: Có lật ngược được quan điểm thông thường không?

Choose a verdict:
- 'HUNT_DEEPER': Hypotheses are good, but evidence still lacks specific numbers/records. Provide specific targeted_search_directive for each flaw.
- 'DISCARD_AND_RETHINK': Hypotheses are fundamentally contradicted or dead-ends.
- 'NO_MORE_FLAWS': Evidence is forensic, solid, and ready for script production.

Select the winning_hypothesis_id (e.g. HYP_01) that currently has the strongest backing.
Count unexplained_contradictions (0 to 5).
"""
    return structured("prosecutor", prompt, ProsecutorIndictment, temperature=0.2)


# =====================================================================
# NODE 6A: SHOWRUNNER MASTER PLAN
# =====================================================================
def run_node_6a_plan(
    winning_hyp: CounterHypothesis,
    vault: List[EvidenceItem],
    language: str
) -> MasterPlan:
    facts_brief = [
        f"[{e.evidence_id}] ({e.source_tier}) {e.factual_claim} (Metric: {e.quantitative_metric}, Time: {e.exact_timestamp_or_date})"
        for e in vault[:20]
    ]

    prompt = f"""You are an Elite Documentary Showrunner writing in the exact style of LEMMINO, FERN, and VERITASIUM.
Language for documentary: '{language}'.
Winning Hypothesis: {winning_hyp.pivot_angle_title} - {winning_hyp.core_argument}
Smoking Gun: {winning_hyp.required_smoking_gun}

Verified Evidence Vault ({len(facts_brief)} facts):
{json.dumps(facts_brief, indent=2, ensure_ascii=False)}

STRICT ANTI-SLOP & VIRAL DOCUMENTARY RULES:
1. NO FICTIONAL CHARACTERS OR FAKE DRAMATIZATION:
   - NEVER invent a fictional "investigator", "detective", "anonymous hospital administrator", or fake interviews!
   - Every single beat MUST be grounded in real documented cases, real clinical experiments, real statutes, and real scientists/institutions from the Evidence Vault.
2. COLD OPEN HOOK (Act 1):
   - Open directly inside a REAL documented case or experiment (specific year, specific place/hospital, specific measurement anomaly that baffled researchers), NEVER with generic melodrama like "In a chaotic emergency room, a family's world shattered...".
3. entity_locks (in style_bible):
   - Create AT LEAST 3 concrete visual anchors (e.g. a real historical figure/scientist, a specific medical device/scanner, a specific laboratory/ICU environment) with detailed 35mm reference_image_prompt.
4. acts: Exactly 5 Act blueprints:
   - Act 1: HOOK (Real documented anomaly cold open, target 12 scenes)
   - Act 2: SETUP (The conventional scientific consensus & how it was established, target 25-30 scenes)
   - Act 3: ESCALATION (The clinical anomalies & smoking gun data from the vault, target 35-40 scenes)
   - Act 4: CLIMAX (The scientific & legal paradigm clash backed by hard numbers, target 30-35 scenes)
   - Act 5: RESOLUTION (What this changes about life and death, target 15-20 scenes)
"""
    return structured("writer_hook", prompt, MasterPlan, temperature=0.3)


# =====================================================================
# NODE 6B & 7: SCENE WRITING & SELF-HEALING VALIDATOR
# =====================================================================
_DIGIT_MAP_EN = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
_DIGIT_MAP_VI = {"0": "không", "1": "một", "2": "hai", "3": "ba", "4": "bốn", "5": "năm", "6": "sáu", "7": "bảy", "8": "tám", "9": "chín"}


def _heal_scene_item(sc: SceneItem, act: ActBlueprint, language: str, entity_tokens: List[str], scene_id: str) -> SceneItem:
    """Tự động chữa lành các lỗi định dạng nhỏ của LLM (trùng scene_id, dính số trong VO, lệch trigger_word, thừa entity)."""
    from core.schemas import BANNED_PHRASES, ParallaxLayers, tokenize
    import re

    sc.scene_id = scene_id
    sc.act_number = act.act_number
    sc.narrative_phase = act.narrative_phase

    if act.narrative_phase == "HOOK":
        sc.visual_mode = "AI_VIDEO"
        if not sc.video_motion_prompt:
            sc.video_motion_prompt = "slow push in"
        if not sc.camera_move:
            sc.camera_move = "SLOW_PUSH_IN"
        if not sc.parallax_spec:
            sc.parallax_spec = ParallaxLayers()
    else:
        # Đảm bảo tỷ lệ AI_VIDEO ở thân bài <= 15% và không vượt trần 6.5s/clip
        num_idx = int(scene_id[1:]) if scene_id[1:].isdigit() else 1
        vo_wc = len(sc.voiceover_text.split())
        if sc.visual_mode == "AI_VIDEO":
            if vo_wc > 14 or (num_idx % 8 != 0):
                sc.visual_mode = "STATIC_PARALLAX"
                if not sc.parallax_spec:
                    sc.parallax_spec = ParallaxLayers()

    # 1. Thay thế chữ số còn sót trong voiceover_text bằng chữ
    dmap = _DIGIT_MAP_VI if language == "vi" else _DIGIT_MAP_EN
    if re.search(r"\d", sc.voiceover_text):
        sc.voiceover_text = re.sub(r"\d", lambda m: f" {dmap[m.group(0)]} ", sc.voiceover_text)
        sc.voiceover_text = re.sub(r"\s+", " ", sc.voiceover_text).strip()

    # 2. Xóa cụm từ cấm nếu LLM lỡ viết vào
    for bp in BANNED_PHRASES.get(language, []):
        sc.voiceover_text = re.sub(re.escape(bp), "", sc.voiceover_text, flags=re.IGNORECASE).strip()

    # 2b. Tinh chỉnh hơi thở ngắt nghỉ (... / —) & thời gian nghỉ lấy hơi cuối cảnh (pause_after_sec)
    try:
        from agents.agent_08_self_learner.prosody_director import analyze_scene_prosody

        p_info = analyze_scene_prosody(sc.voiceover_text, act_phase=act.narrative_phase, pause_after_sec=sc.pause_after_sec)
        sc.voiceover_text = p_info["polished_vo"]
        sc.pause_after_sec = p_info["recommended_pause_after_sec"]
    except Exception:
        pass

    # 3. Khớp trigger_word vào từ thực tế có trong voiceover_text
    vo_words = tokenize(sc.voiceover_text)
    if vo_words:
        for idx, cue in enumerate(sc.audio_cues):
            cw = tokenize(cue.trigger_word)
            if not cw or cw[0] not in vo_words:
                cue.trigger_word = vo_words[min(idx * 2, len(vo_words) - 1)]

    # 4. Chỉ giữ lại reference_entities có trong StyleBible
    valid_set = set(entity_tokens)
    sc.reference_entities = [e for e in sc.reference_entities if e in valid_set]
    return sc


def _vo_jaccard_similarity(text_a: str, text_b: str) -> float:
    import re

    wa = {w for w in re.findall(r"[^\W\d_]+", text_a.lower()) if len(w) > 1}
    wb = {w for w in re.findall(r"[^\W\d_]+", text_b.lower()) if len(w) > 1}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / float(len(wa | wb))


def normalize_all_scenes(scenes: List[SceneItem], plan: MasterPlan, language: str) -> List[SceneItem]:
    """Loại bỏ các cảnh bị trùng/lặp ý và đánh lại số thứ tự S001..S{N} tuyệt đối không trùng lặp trước khi đóng gói MasterScript."""
    entity_tokens = [e.entity_token for e in plan.style_bible.entity_locks]
    act_map = {a.act_number: a for a in plan.acts}
    default_act = plan.acts[0]

    deduped: List[SceneItem] = []
    for sc in scenes:
        is_dup = any(_vo_jaccard_similarity(sc.voiceover_text, prev.voiceover_text) >= 0.62 for prev in deduped)
        if not is_dup:
            deduped.append(sc)

    for idx, sc in enumerate(deduped, 1):
        act = act_map.get(sc.act_number, default_act)
        _heal_scene_item(sc, act, language, entity_tokens, f"S{idx:03d}")
    return deduped


def write_act_scenes_with_healing(
    act: ActBlueprint,
    plan: MasterPlan,
    vault: List[EvidenceItem],
    language: str,
    start_scene_num: int,
    prev_bridge: str,
    existing_scenes: Optional[List[SceneItem]] = None,
    on_batch_saved=None,
) -> Tuple[List[SceneItem], str]:
    """Sinh kịch bản từng Hồi theo batch 8 cảnh, lưu checkpoint ngay sau mỗi batch."""
    facts_brief = [
        {"id": e.evidence_id, "claim": e.factual_claim, "prop": e.tangible_artifact_desc}
        for e in vault[:15]
    ]
    entity_tokens = [e.entity_token for e in plan.style_bible.entity_locks]

    total_scenes_needed = act.target_scene_count
    generated_scenes: List[SceneItem] = list(existing_scenes) if existing_scenes else []
    curr_id = start_scene_num + len(generated_scenes)
    if generated_scenes:
        last_prev = generated_scenes[-1]
        curr_bridge = f"Visual: {last_prev.flux_base_image_prompt[:80]}... | VO: {last_prev.voiceover_text}"
        print(f"    [CHECKPOINT] Tiếp tục Hồi {act.act_number} từ cảnh S{curr_id:03d} (đã có {len(generated_scenes)}/{total_scenes_needed} cảnh)...", flush=True)
    else:
        curr_bridge = prev_bridge

    batch_size = 8
    try:
        from agents.agent_08_self_learner import (
            build_human_memory_prompt_block,
            evaluate_and_self_learn,
            infer_niche_tag,
        )

        niche_tag = infer_niche_tag(
            f"{act.act_title} {' '.join(act.story_beats[:3])} {' '.join(f['claim'] for f in facts_brief[:5])}"
        )
        human_memory_block = build_human_memory_prompt_block(
            niche=niche_tag,
            act_phase=act.narrative_phase,
            query_text=f"{act.act_title} {' '.join(act.story_beats[:3])}",
        )
    except Exception:
        niche_tag = "general"
        human_memory_block = ""

    while len(generated_scenes) < total_scenes_needed:
        remaining = total_scenes_needed - len(generated_scenes)
        count_this_batch = min(batch_size, remaining)
        expected_ids = [f"S{curr_id + i:03d}" for i in range(count_this_batch)]
        already_spoken = [f"[{s.scene_id}] {s.voiceover_text}" for s in generated_scenes[-16:]]
        progress_pct = int((len(generated_scenes) / max(total_scenes_needed, 1)) * 100)

        batch_prompt = f"""You are directing Act {act.act_number}: '{act.act_title}' ({act.narrative_phase}).
Target language for voiceover_text: '{language}'.
Generate EXACTLY {count_this_batch} NEW scenes with Scene IDs: {expected_ids} (Act progress: {progress_pct}% -> {int(((len(generated_scenes)+count_this_batch)/max(total_scenes_needed,1))*100)}%).
Story Beats for this Act: {act.story_beats}
Start from visual bridge: {curr_bridge}
Act cliffhanger (save for the final scenes of this Act): {act.open_loop_cliffhanger}

ALREADY SPOKEN IN THIS ACT (STRICTLY FORBIDDEN TO REPEAT OR PARAPHRASE THESE IDEAS):
{already_spoken if already_spoken else "None yet (opening of this Act)."}
{human_memory_block}
STRICT PRODUCTION LAWS:
1. voiceover_text MUST BE COLD, RAZOR-SHARP INVESTIGATIVE NARRATION (like LEMMINO, FERN, VERITASIUM):
   - NO MELODRAMATIC AI SLOP: Never write cheesy fiction like "In the sterile chaos...", "a chilling silence", "a family's world shattered", "shadowy world", or "the investigator confronts...".
   - NO STAGE DIRECTIONS: Never write "Interview with...", "Show internal memos...", or "The documentary presents...".
   - Write concrete, factual, gripping sentences driven by real dates, real institutions, real experiments, and sharp paradoxes from the Evidence Vault: {facts_brief[:8]}.
   - MANDATORY WORD COUNT PER SCENE (NEVER WRITE CHOPPY TELEGRAPHIC FRAGMENTS!):
     * If language == 'vi' (Vietnamese): EVERY scene voiceover_text MUST be 18 to 32 words long (1 to 2 complete, flowing spoken sentences with full subject-verb-object and conversational transitions like 'Thế nhưng...', 'Nhìn kỹ vào...', 'Trên giấy tờ thì...'). NEVER write choppy 5-8 word fragments!
     * If language == 'en' (English): EVERY scene voiceover_text MUST be 14 to 24 words long (1 to 2 complete, natural spoken sentences).
   - ZERO DIGITS (0-9). Spell out every single number, year, currency as spoken words!
   - Numbers for visual display belong ONLY in on_screen_text!
   - NO AI clichés ('delve into', 'chào mừng các bạn', 'bạn có biết', etc.)
2. visual_mode rules:
   - If narrative_phase == 'HOOK': visual_mode MUST be 'AI_VIDEO'.
   - For Acts 2-5: ~70% MUST be 'STATIC_PARALLAX', ~20% 'DOCUMENT_HIGHLIGHT' or 'KINETIC_DATA_CARD', and at most 10% 'AI_VIDEO'.
   - For 'AI_VIDEO': MUST provide video_motion_prompt, camera_move, AND parallax_spec (as fallback).
   - For 'STATIC_PARALLAX': MUST provide parallax_spec (foreground, midground, background).
   - For 'DOCUMENT_HIGHLIGHT': MUST provide document_asset with source_url and highlight_text.
   - For 'KINETIC_DATA_CARD': MUST provide on_screen_text (e.g. '$412,000').
3. flux_base_image_prompt: MUST be >= 40 words long, in English, with 35mm lens, camera angle, lighting, era details.
4. reference_entities: ONLY use tokens from available entities: {entity_tokens}.
5. audio_cues: 1 to 3 cues. trigger_word MUST be an exact word present in that scene's voiceover_text!
6. evidence_refs: Cite evidence ids like EV_001 from: {[f['id'] for f in facts_brief]}.

Available StyleBible Negative Prompt: {plan.style_bible.negative_prompt}
Style: {plan.style_bible.visual_era_and_tone} | LUT: {plan.style_bible.color_grading_lut}
"""
        batch_scenes = []
        errors_feedback = ""
        for attempt in range(3):
            p = batch_prompt
            if errors_feedback:
                p += f"\n\nPREVIOUS ATTEMPT HAD THESE VALIDATION ERRORS. FIX THEM COMPLETELY:\n{errors_feedback}"
            try:
                role_name = "writer_hook" if act.act_number == 1 else "writer"
                res = structured(role_name, p, ActScenes, temperature=0.3)
                valid_batch = []
                batch_errs = []
                for idx_sc, sc in enumerate(res.scenes[:count_this_batch]):
                    sid = f"S{curr_id + idx_sc:03d}"
                    _heal_scene_item(sc, act, language, entity_tokens, sid)
                    try:
                        sc.validate_for(language)
                        vo_wc = len(sc.voiceover_text.split())
                        min_words_needed = 16 if language == "vi" else 13
                        if vo_wc < min_words_needed and attempt < 2:
                            raise ValueError(
                                f"voiceover_text is too short and choppy ({vo_wc} words < {min_words_needed} words). "
                                f"Rewrite {sc.scene_id} as a complete, flowing conversational thought ({min_words_needed} to 30 words) with full subject-verb context and smooth storytelling transition!"
                            )
                        if attempt < 2 and any(
                            _vo_jaccard_similarity(sc.voiceover_text, prev.voiceover_text) >= 0.58
                            for prev in (generated_scenes + valid_batch)
                        ):
                            raise ValueError(
                                f"voiceover_text repeats/paraphrases an already spoken scene! "
                                f"Advance the story with a BRAND NEW fact or detail instead of repeating '{sc.voiceover_text[:55]}...'."
                            )
                        valid_batch.append(sc)
                    except Exception as ve:
                        batch_errs.append(f"Scene {sc.scene_id}: {str(ve)}")

                if valid_batch and not batch_errs:
                    batch_scenes = valid_batch
                    break
                else:
                    errors_feedback = "\n".join(batch_errs) if batch_errs else "Empty scenes returned"
            except Exception as e:
                errors_feedback = f"JSON/Parsing error: {str(e)[:250]}"
                time.sleep(1.0)

        if not batch_scenes:
            if 'valid_batch' in locals() and valid_batch:
                batch_scenes = valid_batch

        if batch_scenes:
            generated_scenes.extend(batch_scenes)
            curr_id += len(batch_scenes)
            last = batch_scenes[-1]
            curr_bridge = f"Visual: {last.flux_base_image_prompt[:80]}... | VO: {last.voiceover_text}"
            if on_batch_saved:
                on_batch_saved(generated_scenes, curr_bridge)
            print(f"    + Đã viết xong {len(generated_scenes)}/{total_scenes_needed} cảnh (đến {last.scene_id})", flush=True)
        else:
            break

    if generated_scenes:
        try:
            from agents.agent_08_self_learner import evaluate_and_self_learn

            cadence_metrics = evaluate_and_self_learn(
                voiceover_texts=[s.voiceover_text for s in generated_scenes],
                niche=niche_tag,
                act_phase=act.narrative_phase,
            )
            print(
                f"    [Self-Learner] Hồi {act.act_number} ({act.narrative_phase}) | "
                f"Human Score: {cadence_metrics['human_score']}/10 | "
                f"Burstiness (σ): {cadence_metrics['burstiness']} | "
                f"Stance Markers: {cadence_metrics['stance_hits']}",
                flush=True,
            )
        except Exception:
            pass

    return generated_scenes, curr_bridge


# =====================================================================
# QUẢN LÝ CHECKPOINT (RESUME KHI LỖI ĐỂ KHÔNG TỐN TIỀN CHẠY LẠI TỪ ĐẦU)
# =====================================================================
def _checkpoint_path(youtube_url: str, language: str) -> Path:
    import hashlib
    import re

    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", youtube_url)
    vid = m.group(1) if m else hashlib.sha1(youtube_url.strip().encode("utf-8")).hexdigest()[:12]
    ckpt_dir = ROOT / ".cache" / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    return ckpt_dir / f"ckpt_{vid}_{language}.json"


def _load_ckpt(path: Path) -> Dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_ckpt(path: Path, data: Dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# =====================================================================
# QUY TRÌNH TỰ ĐỘNG CHÍNH (THE AUTONOMOUS GRAPH PIPELINE)
# =====================================================================
def run_autonomous_brain(
    youtube_url: str,
    manual_transcript_path: Optional[str] = None,
    language: str = "en",
    auto_approve_gate: bool = True,
    fresh: bool = False,
    rewrite_acts: bool = False,
) -> Path:
    """Chạy toàn bộ đồ thị tự phản biện từ URL/Transcript đến gói xuất xưởng Phase 2 (có Checkpoint Resume)."""
    ckpt_file = _checkpoint_path(youtube_url, language)
    if fresh and ckpt_file.exists():
        ckpt_file.unlink()
    ckpt = _load_ckpt(ckpt_file)
    if rewrite_acts:
        ckpt.pop("master_plan", None)
        ckpt.pop("acts", None)
        ckpt["run_id"] = f"run-{language}-{time.strftime('%Y%m%d-%H%M%S')}"
        _save_ckpt(ckpt_file, ckpt)

    run_id = ckpt.get("run_id") or f"run-{language}-{time.strftime('%Y%m%d-%H%M%S')}"
    ckpt["run_id"] = run_id
    _save_ckpt(ckpt_file, ckpt)

    print(f"\n{'='*70}\n[KHỞI ĐỘNG AUTONOMOUS BRAIN v3.1] Run ID: {run_id} | Ngôn ngữ: {language.upper()}\n{'='*70}")
    if len(ckpt) > 1:
        print(f"[CHECKPOINT] Tìm thấy tiến trình lưu tại: {ckpt_file.name} (chạy tiếp từ bước dừng)")

    # BƯỚC 1: Lấy dữ liệu & Bóc tách
    print("\n--- [NODE 1: MULTIMODAL AUTOPSY] ---")
    if "video_input" in ckpt and "autopsy" in ckpt:
        video_input = ckpt["video_input"]
        autopsy = RivalAutopsyReport.model_validate(ckpt["autopsy"])
        print(f"  [CHECKPOINT] Khôi phục Node 1 ({video_input.get('title')}) — tốn $0")
    else:
        video_input = build_input(youtube_url, manual_transcript_path)
        print(f"Tiêu đề: {video_input.get('title')}")
        print(f"Nguồn: {video_input.get('source')} | Từ: {len(video_input.get('transcript', '').split())} | Bình luận: {len(video_input.get('comments', []))}")
        autopsy = run_node_1_autopsy(video_input, language)
        ckpt["video_input"] = video_input
        ckpt["autopsy"] = autopsy.model_dump()
        _save_ckpt(ckpt_file, ckpt)
    print(f"Luận điểm đối thủ: {autopsy.rival_core_thesis}")

    # BƯỚC 2: Kiến trúc sư Giả thuyết
    print("\n--- [NODE 2: COUNTER-HYPOTHESIS ARCHITECT] ---")
    if "hypotheses" in ckpt:
        hypotheses = [CounterHypothesis.model_validate(h) for h in ckpt["hypotheses"]]
        print(f"  [CHECKPOINT] Khôi phục Node 2 ({len(hypotheses)} giả thuyết) — tốn $0")
    else:
        hypotheses = run_node_2_architect(autopsy)
        ckpt["hypotheses"] = [h.model_dump() for h in hypotheses]
        _save_ckpt(ckpt_file, ckpt)
    for h in hypotheses:
        print(f"  [{h.hypothesis_id}] {h.pivot_angle_title}: {h.core_argument[:100]}...")

    # BƯỚC 3 & 4: Vòng lặp Săn Bằng chứng & Công tố viên Phản biện
    debate_ckpt = ckpt.get("debate", {})
    if debate_ckpt.get("completed"):
        vault = [EvidenceItem.model_validate(e) for e in debate_ckpt["vault"]]
        winning_hyp = CounterHypothesis.model_validate(debate_ckpt["winning_hyp"])
        exit_reason = debate_ckpt.get("exit_reason", "PASSED")
        print(f"\n--- [NODE 3 & 4: TRANH BIỆN PHÁP Y] ---")
        print(f"  [CHECKPOINT] Khôi phục Hồ sơ bằng chứng ({len(vault)} facts, FSS={compute_fss(vault):.2f}) — tốn $0")
    else:
        vault = [EvidenceItem.model_validate(e) for e in debate_ckpt.get("vault", [])]
        past_keys = fact_keys(vault)
        winning_hyp = CounterHypothesis.model_validate(debate_ckpt["winning_hyp"]) if "winning_hyp" in debate_ckpt else hypotheses[0]
        exit_reason = "MAX_ROUNDS"
        start_round = int(debate_ckpt.get("last_round", 0)) + 1
        indictment = ProsecutorIndictment.model_validate(debate_ckpt["indictment"]) if "indictment" in debate_ckpt else None

        for round_num in range(start_round, 3):
            print(f"\n--- [VÒNG TRANH BIỆN {round_num}/2: SĂN BẰNG CHỨNG & PHẢN BIỆN] ---")
            with ThreadPoolExecutor(max_workers=3) as executor:
                if round_num == 1 or not indictment:
                    futures = [executor.submit(run_single_hunter, h, h.initial_search_vectors) for h in hypotheses]
                else:
                    directives = [flaw.targeted_search_directive for flaw in indictment.identified_flaws] or winning_hyp.initial_search_vectors
                    futures = [executor.submit(run_single_hunter, winning_hyp, directives)]

                for f in futures:
                    vault.extend(f.result())

            vault = dedupe_facts(vault)
            for i, item in enumerate(vault, 1):
                item.evidence_id = f"EV_{i:03d}"

            curr_fss = compute_fss(vault)
            new_facts = new_unique_facts(past_keys, vault)
            past_keys = fact_keys(vault)
            print(f"Kho bằng chứng hiện tại: {len(vault)} facts | Facts mới: {new_facts} | FSS: {curr_fss:.2f}")

            indictment = run_node_4_prosecutor(hypotheses, vault, round_num, curr_fss)
            print(f"Phán quyết Công tố viên: {indictment.verdict} | Thắng thế: {indictment.winning_hypothesis_id}")
            for flaw in indictment.identified_flaws:
                print(f"  - [{flaw.flaw_type}] {flaw.critique_detail[:120]}")

            for h in hypotheses:
                if h.hypothesis_id == indictment.winning_hypothesis_id:
                    winning_hyp = h
                    break

            done_debate = False
            if indictment.verdict == "NO_MORE_FLAWS" or passed(vault):
                exit_reason = "PASSED"
                done_debate = True
                print(">>> Hồ sơ bằng chứng ĐẠT CHUẨN ĐẶC TẢ PHÁP Y.")
            elif new_facts < 2 and round_num > 1:
                exit_reason = "SATURATED"
                done_debate = True
                print(">>> Thông tin đã bão hòa. Dừng đào sâu.")
            elif round_num >= 2:
                done_debate = True

            ckpt["debate"] = {
                "vault": [e.model_dump() for e in vault],
                "winning_hyp": winning_hyp.model_dump(),
                "indictment": indictment.model_dump(),
                "last_round": round_num,
                "exit_reason": exit_reason,
                "completed": done_debate,
            }
            _save_ckpt(ckpt_file, ckpt)
            if done_debate:
                break

    # BƯỚC 5: HUMAN GATE
    print("\n--- [NODE 5: DOSSIER LOCK & HUMAN GATE] ---")
    print(f"Giả thuyết được phê duyệt: [{winning_hyp.hypothesis_id}] {winning_hyp.pivot_angle_title}")
    print(f"Số bằng chứng đã xác minh: {len(vault)} | Điểm FSS: {compute_fss(vault):.2f} | Lý do kết thúc: {exit_reason}")
    if not auto_approve_gate:
        input("Nhấn ENTER trên bàn phím để xác nhận mở khóa Phòng Biên kịch (hoặc Ctrl+C để dừng)... ")

    # BƯỚC 6A: Lập MasterShowrunnerPlan (5 Hồi + StyleBible)
    print("\n--- [NODE 6A: SHOWRUNNER MASTER PLAN] ---")
    if "master_plan" in ckpt:
        master_plan = MasterPlan.model_validate(ckpt["master_plan"])
        print("  [CHECKPOINT] Khôi phục Master Plan 5 Hồi & StyleBible — tốn $0")
    else:
        master_plan = run_node_6a_plan(winning_hyp, vault, language)
        ckpt["master_plan"] = master_plan.model_dump()
        _save_ckpt(ckpt_file, ckpt)

    print(f"Ý tưởng Thumbnail: {master_plan.thumbnail_concept}")
    print(f"Thực thể cố định (Entity Locks): {[e.entity_token for e in master_plan.style_bible.entity_locks]}")
    for act in master_plan.acts:
        print(f"  Hồi {act.act_number}: {act.act_title} ({act.narrative_phase}) - {act.target_scene_count} cảnh")

    # BƯỚC 6B & 7: Viết kịch bản chi tiết từng cảnh & Tự động sửa lỗi (có lưu từng batch)
    print("\n--- [NODE 6B & 7: ACT-BY-ACT SCRIPT GENERATION & HEALING] ---")
    all_scenes: List[SceneItem] = []
    bridge = "COLD OPEN inside a physical room at the exact second something goes wrong."
    scene_counter = 1
    acts_ckpt = ckpt.setdefault("acts", {})

    for act in master_plan.acts:
        act_key = str(act.act_number)
        saved_act = acts_ckpt.get(act_key, {})
        saved_scenes = [SceneItem.model_validate(s) for s in saved_act.get("scenes", [])]

        if len(saved_scenes) >= act.target_scene_count:
            print(f"  [CHECKPOINT] Khôi phục Hồi {act.act_number}/5 ({len(saved_scenes)} cảnh) — tốn $0")
            all_scenes.extend(saved_scenes)
            scene_counter += len(saved_scenes)
            bridge = saved_act.get("bridge", bridge)
            continue

        print(f"Đang biên kịch Hồi {act.act_number}/5: {act.act_title}...")

        def _save_batch_progress(curr_scenes: List[SceneItem], curr_b: str, _ak=act_key):
            acts_ckpt[_ak] = {
                "scenes": [s.model_dump() for s in curr_scenes],
                "bridge": curr_b,
            }
            _save_ckpt(ckpt_file, ckpt)

        act_scenes, bridge = write_act_scenes_with_healing(
            act=act,
            plan=master_plan,
            vault=vault,
            language=language,
            start_scene_num=scene_counter,
            prev_bridge=bridge,
            existing_scenes=saved_scenes,
            on_batch_saved=_save_batch_progress,
        )
        all_scenes.extend(act_scenes)
        scene_counter += len(act_scenes)
        print(f"  -> Xong {len(act_scenes)} cảnh cho Hồi {act.act_number}.")

    all_scenes = normalize_all_scenes(all_scenes, master_plan, language)
    script = MasterScript(
        run_id=run_id,
        language=language,
        source_rival_url=youtube_url,
        plan=master_plan,
        scenes=all_scenes
    )

    # BƯỚC 8: ĐÓNG GÓI XUẤT XƯỞNG (ASSEMBLER)
    print("\n--- [NODE 8: PRODUCTION PACKAGE ASSEMBLER] ---")
    package_dir = ROOT / "production_package"
    final_output_path = assemble_package(
        script=script,
        evidence=vault,
        out_root=package_dir,
        quality={"exit_reason": exit_reason, "fss_score": compute_fss(vault)},
        models_used={"autopsy": "auto", "architect": "auto", "prosecutor": "auto", "writer": "auto"}
    )

    print(f"\n{'='*70}")
    print(f"XUẤT XƯỞNG THÀNH CÔNG GIAI ĐOẠN 1!")
    print(f"Thư mục bàn giao cho Phase 2: {final_output_path}")
    print(f"Tổng số cảnh: {len(all_scenes)} cảnh | Thời lượng ước tính: {script.estimated_total_duration_sec}s")
    print(f"{'='*70}\n")
    return final_output_path
