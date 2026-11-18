"""HumanVoiceCritic & Burstiness Scorer — Chấm điểm 'Độ Giống Người' và Bơm Ký Ức Động (Dynamic Few-Shot).
Kết nối trực tiếp với SQLiteFTS5MemoryBackend để:
1. Truy xuất Top mẫu câu người thật (< 1.5ms) theo đúng Ngách + Hồi kịch bản.
2. Đo chỉ số Burstiness (độ biến thiên nhịp câu dài - ngắn) và mật độ chính kiến cá nhân (Stance).
3. Tự động tích lũy các câu xuất sắc mới vào script_brain.db sau mỗi lần chạy.
"""
import math
import re
from typing import Dict, List, Optional

from agents.agent_08_self_learner.memory_backend import SQLiteFTS5MemoryBackend

SLIDE_CLICHES = (
    "interview with",
    "show internal",
    "the documentary",
    "this scene",
    "furthermore",
    "moreover",
    "in conclusion",
    "additionally",
    "it is important to note",
    "in the sterile chaos",
    "a chilling silence",
    "world shattered",
)

HUMAN_STANCE_MARKERS = (
    "on paper",
    "in reality",
    "except",
    "wait",
    "look at",
    "pause",
    "think about",
    "here is the",
    "makes zero sense",
    "nobody asked",
    "at least",
    "thế nhưng",
    "nhưng thực tế",
    "khoan đã",
    "nhìn kỹ",
    "trên giấy tờ",
    "nghĩ mà xem",
)


def infer_niche_tag(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("football", "soccer", "premier league", "transfer", "club", "goal", "coach", "manager", "fifa", "champions league")):
        return "football"
    if any(k in low for k in ("netflix", "episode", "season", "villain", "character", "movie", "director", "ending explained", "plot")):
        return "netflix"
    if any(k in low for k in ("gta", "los santos", "rockstar", "red dead", "npc", "player", "map", "gameplay", "game")):
        return "gta"
    return "general"


def score_human_cadence(voiceover_texts: List[str]) -> Dict[str, float]:
    """Đo định lượng Độ Giống Người (Human Score thang 10) dựa trên Burstiness, Stance Markers và Anti-Slide."""
    if not voiceover_texts:
        return {"human_score": 5.0, "burstiness": 0.0, "stance_hits": 0, "slide_penalties": 0}

    all_sentences: List[str] = []
    scene_word_counts: List[int] = []
    for vo in voiceover_texts:
        scene_word_counts.append(len(vo.split()))
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", vo.strip()) if s.strip()]
        all_sentences.extend(sents)

    lengths = [len(s.split()) for s in all_sentences if s]
    if len(lengths) >= 2:
        mean_l = sum(lengths) / len(lengths)
        variance = sum((x - mean_l) ** 2 for x in lengths) / len(lengths)
        std_dev = math.sqrt(variance)
    else:
        std_dev = 3.5

    joined_low = " ".join(voiceover_texts).lower()
    stance_hits = sum(1 for m in HUMAN_STANCE_MARKERS if m in joined_low)
    punct_hits = joined_low.count("?") + joined_low.count("—") + joined_low.count("...")
    slide_penalties = sum(1 for c in SLIDE_CLICHES if c in joined_low)
    # Phạt nặng nếu cảnh bị viết cụt ngủn kiểu điện tín (< 11 từ/cảnh)
    choppy_scenes = sum(1 for wc in scene_word_counts if wc < 11)
    has_long_anchor = any(l >= 10 for l in lengths)
    has_short_punch = any(2 <= l <= 7 for l in lengths) and has_long_anchor

    base = 6.8
    burst_bonus = min(1.8, std_dev / 2.8) + (0.6 if has_short_punch else 0.0)
    stance_bonus = min(1.5, (stance_hits * 0.45) + (punct_hits * 0.2))
    penalty = (slide_penalties * 1.5) + (choppy_scenes * 0.9) + (0.0 if has_long_anchor else 1.2)

    final_score = max(1.0, min(10.0, round(base + burst_bonus + stance_bonus - penalty, 2)))
    return {
        "human_score": final_score,
        "burstiness": round(std_dev, 2),
        "stance_hits": stance_hits + punct_hits,
        "slide_penalties": slide_penalties,
    }


def build_human_memory_prompt_block(
    niche: str,
    act_phase: str,
    query_text: str,
    brain: Optional[SQLiteFTS5MemoryBackend] = None,
) -> str:
    """Truy xuất SQLite FTS5 (< 1.5ms) và đóng gói thành khối huấn luyện Few-Shot cho LLM."""
    mem = brain or SQLiteFTS5MemoryBackend()
    records = mem.retrieve_context(niche=niche, act_phase=act_phase, query_text=query_text, top_k=4)

    lines = [
        "\n=====================================================================",
        f"🧠 HUMAN VOICE & SELF-LEARNING MEMORY BANK (Niche: {niche.upper()} | Phase: {act_phase})",
        "=====================================================================",
        "TWO-PASS MENTAL PROCESS (CRITICAL TO SOUND LIKE A REAL HUMAN NARRATOR):",
        "Step A: First, speak this segment in your head as ONE flowing, opinionated human storytelling monologue.",
        "        - NEVER write choppy telegraphic fragments like 'Two AM. Heart stops. But EEG explodes.' -> That sounds robotic and broken!",
        "        - EVERY SINGLE SCENE's voiceover_text MUST be a rich, complete, natural conversational thought of 18 to 32 words (Vietnamese) or 14 to 24 words (English).",
        "        - TRUE BURSTINESS WITHIN EACH SCENE: Pair a complete, detailed narrative sentence (14-22 words with real subjects, verbs, and context) WITH a sharp, opinionated human turn or short punchline ('Thế nhưng nhìn vào băng ghi hình xem...', 'Trên giấy tờ là vậy, nhưng thực tế thì ngược lại hoàn toàn.', 'Wait—look closer at that timestamp.').",
        "        - Connect scenes smoothly with conversational transitions ('Và kỳ lạ hơn nữa là...', 'Chưa dừng lại ở đó...', 'Nhưng khoan đã—', 'And here is where the official story falls apart...').",
        "Step B: Place each 18-to-32-word natural conversational segment into each SceneItem.",
        "\n LEARN FROM THESE GOLDEN HUMAN EXAMPLES IN YOUR MEMORY BANK:",
    ]

    for idx, r in enumerate(records, 1):
        if r.get("bad_slide_text"):
            lines.append(f"  Example {idx} [❌ NEVER WRITE SLIDE-STYLE LIKE THIS]: \"{r['bad_slide_text']}\"")
        lines.append(f"  Example {idx} [✅ WRITE HUMAN-STYLE LIKE THIS]: \"{r['human_gold_text']}\"")
        if r.get("why_it_works"):
            lines.append(f"     -> Rule: {r['why_it_works']}")

    lines.append("=====================================================================\n")
    return "\n".join(lines)


def evaluate_and_self_learn(
    voiceover_texts: List[str],
    niche: str,
    act_phase: str,
    brain: Optional[SQLiteFTS5MemoryBackend] = None,
) -> Dict[str, float]:
    """Chấm điểm kịch bản vừa sinh và tự động lưu các câu xuất sắc nhất vào SQLiteFTS5MemoryBackend."""
    mem = brain or SQLiteFTS5MemoryBackend()
    metrics = score_human_cadence(voiceover_texts)

    for vo in voiceover_texts:
        low = vo.lower()
        if any(c in low for c in SLIDE_CLICHES):
            continue
        if len(vo.split()) < 16:
            continue
        has_marker = any(m in low for m in HUMAN_STANCE_MARKERS) or ("?" in vo) or ("—" in vo)
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", vo.strip()) if s.strip()]
        has_long = any(len(s.split()) >= 12 for s in sents)
        if has_marker and has_long and len(sents) >= 2:
            mem.add_memory(
                memory_type="GOLDEN",
                niche=niche,
                act_phase=act_phase,
                human_gold_text=vo,
                why_it_works="Tự học từ kịch bản đạt điểm Burstiness & Stance cao (câu ngắn đan xen câu bình luận sắc bén).",
                burstiness_score=metrics["human_score"],
                win_score=18.0,
            )
            break

    return metrics
