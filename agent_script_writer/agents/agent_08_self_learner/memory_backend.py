"""SQLiteFTS5MemoryBackend — Bộ nhớ dài hạn chuẩn FTS5 BM25 (< 2ms) cho Agent Biên kịch Tự học.
Lưu trữ tại: agent_script_writer/memory_bank/script_brain.db
Hỗ trợ 3 luồng tự học:
1. Auto-Miner: Tự học các câu có nhịp điệu cuốn nhất từ transcript của video triệu view thật.
2. Anti-Slide Critic: Ghi nhớ các câu thô kiểu 'đọc slide' từng bị loại để không bao giờ lặp lại.
3. User Correction Hook: Học trực tiếp từ các câu do người dùng sửa tay trên giao diện UI (win_score = 100).
"""
import datetime
import re
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_DIR = Path(__file__).resolve().parents[2] / "memory_bank"
DEFAULT_DB_PATH = MEMORY_DIR / "script_brain.db"

SEED_MEMORIES: List[Dict] = [
    # --- NGÁCH 1: BÓNG ĐÁ (FOOTBALL DRAMA / CYNICAL INSIDER) ---
    {
        "memory_type": "GOLDEN",
        "niche": "football",
        "act_phase": "HOOK",
        "persona_tone": "sarcastic_sharp",
        "topic_keywords": "transfer fee contract flop dressing room manager",
        "bad_slide_text": "The club signed the player for a massive transfer fee, but his performance declined rapidly.",
        "human_gold_text": "Eighty-five million euros. On paper, that buys you a generational superstar. In reality? It bought the most expensive benchwarmer in football history—and the leaked dressing room logs explain why.",
        "why_it_works": "Mở đầu bằng con số đắt giá đứng độc lập (3 từ) -> Đặt kỳ vọng 'On paper...' -> Bẻ gãy bằng câu hỏi 'In reality?'.",
        "burstiness_score": 9.4,
        "win_score": 25.0,
    },
    {
        "memory_type": "GOLDEN",
        "niche": "football",
        "act_phase": "CLIMAX",
        "persona_tone": "sarcastic_sharp",
        "topic_keywords": "tactical mistake midfield collapse final match",
        "bad_slide_text": "The coach made a major tactical error in the second half that caused the team to lose.",
        "human_gold_text": "Pause the match footage right at minute sixty-two. Look at the thirty-yard gap between the midfielders. That isn't bad luck—that is a tactical suicide note.",
        "why_it_works": "Ra lệnh trực tiếp cho mắt người xem ('Pause the footage...', 'Look at...') + Ẩn dụ sắc lẹm ('tactical suicide note').",
        "burstiness_score": 9.2,
        "win_score": 22.0,
    },
    # --- NGÁCH 2: PHIM NETFLIX / HOLLYWOOD (COLD FORENSIC / VILLAIN BREAKDOWN) ---
    {
        "memory_type": "GOLDEN",
        "niche": "netflix",
        "act_phase": "HOOK",
        "persona_tone": "cold_forensic",
        "topic_keywords": "villain detail episode hidden clue ending explained",
        "bad_slide_text": "In the first episode, the main antagonist hides his true evil intentions from everyone.",
        "human_gold_text": "Go back to episode one—fourteen minutes in. Before anyone dies, before a single lie is spoken... watch his left hand. He already knew.",
        "why_it_works": "Chỉ thẳng vào một chi tiết cực nhỏ ở đầu phim + Kết bằng câu đinh 3 từ lạnh người ('He already knew.').",
        "burstiness_score": 9.6,
        "win_score": 28.0,
    },
    {
        "memory_type": "GOLDEN",
        "niche": "netflix",
        "act_phase": "ESCALATION",
        "persona_tone": "cold_forensic",
        "topic_keywords": "twist manipulation motive psychology",
        "bad_slide_text": "This scene demonstrates that the character was manipulating his friends the entire time.",
        "human_gold_text": "And here is the detail almost everyone missed on the first watch. He wasn't trying to escape the trap. He built it.",
        "why_it_works": "Đánh vào tâm lý sợ bỏ lỡ ('the detail almost everyone missed') + Cặp câu đối lập cực ngắn ('He wasn't... He built it.').",
        "burstiness_score": 9.5,
        "win_score": 26.0,
    },
    # --- NGÁCH 3: ĐIỀU TRA GAME GTA / RDR2 (CURIOUS EXPLORER) ---
    {
        "memory_type": "GOLDEN",
        "niche": "gta",
        "act_phase": "HOOK",
        "persona_tone": "curious_explorer",
        "topic_keywords": "los santos map secret power station river npc",
        "bad_slide_text": "Grand Theft Auto Five has a very detailed map with many locations that players ignore.",
        "human_gold_text": "For ten years, millions of players have sped past this rusty power station in East Los Santos without looking twice. So I decided to follow the wires—and what Rockstar hid at the end makes zero sense.",
        "why_it_works": "Bắt đầu từ một địa điểm quen thuộc ai cũng lướt qua -> Kể hành động tự mình đi kiểm chứng ('So I decided to...').",
        "burstiness_score": 9.3,
        "win_score": 24.0,
    },
    {
        "memory_type": "GOLDEN",
        "niche": "gta",
        "act_phase": "ESCALATION",
        "persona_tone": "curious_explorer",
        "topic_keywords": "mystery clue abandoned mine serial number easter egg",
        "bad_slide_text": "The developers placed a secret clue on the wall inside the abandoned building.",
        "human_gold_text": "Wait—zoom in on the concrete wall behind the crate. Why would a developer spend forty hours modeling a scratched serial number inside a room you aren't even supposed to enter?",
        "why_it_works": "Ngắt nhịp bằng 'Wait—' + Đặt câu hỏi tu từ xoáy vào ý đồ của nhà phát triển game.",
        "burstiness_score": 9.1,
        "win_score": 21.0,
    },
    # --- NGÁCH 4: TÀI LIỆU ĐIỀU TRA / Y SINH / TÀI CHÍNH (GENERAL / MEDICAL / FINANCE) ---
    {
        "memory_type": "GOLDEN",
        "niche": "general",
        "act_phase": "HOOK",
        "persona_tone": "cold_forensic",
        "topic_keywords": "hospital flatline cardiac arrest brain scanner eeg gamma",
        "bad_slide_text": "The frantic beeping flatlined. In the sterile chaos of the emergency room, a life slipped away, leaving behind a chilling silence.",
        "human_gold_text": "In February two thousand sixteen, an eighty-seven-year-old patient in Vancouver flatlined. Doctors called the time of death. Except someone forgot to turn off the brain scanner strapped to his skull—and thirty seconds later, it erupted.",
        "why_it_works": "Không dùng tính từ sến ('sterile chaos', 'chilling silence'). Mở màn bằng tháng/năm thật, địa điểm thật, và nghịch lý máy móc thật.",
        "burstiness_score": 9.7,
        "win_score": 30.0,
    },
    {
        "memory_type": "GOLDEN",
        "niche": "general",
        "act_phase": "SETUP",
        "persona_tone": "sarcastic_sharp",
        "topic_keywords": "official report protocol law regulation",
        "bad_slide_text": "The official guidelines state that the procedure is completely safe and regulated.",
        "human_gold_text": "At least, that is the comforting story printed in the brochure. But open the regulatory filing from page fourteen, and that entire narrative falls apart.",
        "why_it_works": "Bóc mẽ sự đối lập giữa lời quảng cáo ('comforting story in the brochure') và hồ sơ thật ('page fourteen').",
        "burstiness_score": 9.0,
        "win_score": 20.0,
    },
    {
        "memory_type": "GOLDEN",
        "niche": "general",
        "act_phase": "RESOLUTION",
        "persona_tone": "cold_forensic",
        "topic_keywords": "aftermath question reform truth",
        "bad_slide_text": "The documentary shows that reforms are needed to fix this complex issue in society.",
        "human_gold_text": "Nobody was fired. Not a single statute was rewritten. The machines are still humming in the basement—and the clock is still ticking.",
        "why_it_works": "Hai câu ngắn dứt khoát ('Nobody was fired. Not a single statute...') tạo dư âm ám ảnh thay vì tóm tắt giáo điều.",
        "burstiness_score": 9.4,
        "win_score": 25.0,
    },
    # --- MẪU TIẾNG VIỆT CHUẨN NGƯỜI THẬT (ĐỦ Ý, CÓ NHỊP DÀI - NGẮN ĐAN XEN, KHÔNG CỤT NGỦN) ---
    {
        "memory_type": "GOLDEN",
        "niche": "general",
        "act_phase": "HOOK",
        "persona_tone": "cold_forensic",
        "topic_keywords": "hồ sơ bệnh viện biên bản tử vong lệch giờ sóng não gamma",
        "bad_slide_text": "Hai giờ sáng. Tim ngừng đập. Nhưng máy đo điện não lại bùng nổ.",
        "human_gold_text": "Đúng hai giờ mười bốn phút sáng tại phòng hồi sức Vancouver, tim của một bệnh nhân tám mươi bảy tuổi đã ngừng đập hoàn toàn. Về mặt pháp lý, các bác sĩ kết luận ông ấy đã chết. Thế nhưng chiếc máy đo điện não vô tình chưa rút điện trên đầu ông ấy... lại vừa ghi nhận một cơn bão sóng gamma cực mạnh.",
        "why_it_works": "Tuyệt đối KHÔNG viết cụt ngủn kiểu điện tín ('Hai giờ sáng. Tim ngừng đập.'). Phải dẫn dắt đủ bối cảnh (địa điểm, nhân vật, hành động) rồi lật kèo bằng 'Thế nhưng...' kèm nhịp ngập ngừng '...'.",
        "burstiness_score": 9.7,
        "win_score": 35.0,
    },
    {
        "memory_type": "GOLDEN",
        "niche": "general",
        "act_phase": "HOOK",
        "persona_tone": "sarcastic_sharp",
        "topic_keywords": "báo cáo y khoa hồ sơ giải phẫu mâu thuẫn thời điểm tử vong",
        "bad_slide_text": "Pháp lý xác nhận tử vong. Nhưng kết quả đo điện não nói khác.",
        "human_gold_text": "Trên giấy tờ bệnh án, ranh giới giữa sự sống và cái chết chỉ là một đường kẻ thẳng tắp trên màn hình theo dõi nhịp tim. Nghe thì có vẻ rất rõ ràng và dứt khoát. Nhưng khi các nhà thần kinh học mở băng ghi dữ liệu não bộ sau thời điểm ngừng tim ba mươi giây, toàn bộ định nghĩa y khoa hàng trăm năm qua bỗng nhiên sụp đổ.",
        "why_it_works": "Mở đầu bằng nhận định thông thường ('Trên giấy tờ bệnh án...') -> Đệm một câu nhận xét ngắn đời thường ('Nghe thì có vẻ rất rõ ràng.') -> Tung cú lật bằng câu dài giàu hình ảnh.",
        "burstiness_score": 9.6,
        "win_score": 33.0,
    },
]


def _sanitize_fts_query(raw_text: str) -> str:
    tokens = [w for w in re.findall(r"[A-Za-zÀ-ỹ]{4,}", raw_text.lower())][:8]
    if not tokens:
        return ""
    return " OR ".join(dict.fromkeys(tokens))


class SQLiteFTS5MemoryBackend:
    """Bộ lưu trữ và truy xuất ký ức văn phong bằng SQLite FTS5 BM25 + B-Tree Metadata Index."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema_and_seed()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema_and_seed(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL,
                    niche TEXT NOT NULL,
                    act_phase TEXT NOT NULL,
                    persona_tone TEXT NOT NULL,
                    topic_keywords TEXT DEFAULT '',
                    bad_slide_text TEXT DEFAULT '',
                    human_gold_text TEXT NOT NULL,
                    why_it_works TEXT DEFAULT '',
                    burstiness_score REAL DEFAULT 8.5,
                    win_score REAL DEFAULT 10.0,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_mem_lookup
                ON memory_entries(niche, act_phase, memory_type, win_score DESC);

                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                    topic_keywords,
                    human_gold_text,
                    why_it_works,
                    content='memory_entries',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );

                CREATE TRIGGER IF NOT EXISTS mem_ai AFTER INSERT ON memory_entries BEGIN
                    INSERT INTO memory_fts(rowid, topic_keywords, human_gold_text, why_it_works)
                    VALUES (new.id, new.topic_keywords, new.human_gold_text, new.why_it_works);
                END;

                CREATE TRIGGER IF NOT EXISTS mem_ad AFTER DELETE ON memory_entries BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, topic_keywords, human_gold_text, why_it_works)
                    VALUES ('delete', old.id, old.topic_keywords, old.human_gold_text, old.why_it_works);
                END;

                CREATE TRIGGER IF NOT EXISTS mem_au AFTER UPDATE ON memory_entries BEGIN
                    INSERT INTO memory_fts(memory_fts, rowid, topic_keywords, human_gold_text, why_it_works)
                    VALUES ('delete', old.id, old.topic_keywords, old.human_gold_text, old.why_it_works);
                    INSERT INTO memory_fts(rowid, topic_keywords, human_gold_text, why_it_works)
                    VALUES (new.id, new.topic_keywords, new.human_gold_text, new.why_it_works);
                END;
                """
            )
            # Luôn đảm bảo các SEED_MEMORIES chuẩn mới nhất có mặt trong DB và dọn sạch các câu tự học bị cụt ngủn (< 90 ký tự)
            conn.execute(
                "DELETE FROM memory_entries WHERE memory_type = 'GOLDEN' AND length(human_gold_text) < 90"
            )
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            for item in SEED_MEMORIES:
                exists = conn.execute(
                    "SELECT id FROM memory_entries WHERE human_gold_text = ? LIMIT 1",
                    (item["human_gold_text"],),
                ).fetchone()
                if not exists:
                    conn.execute(
                        """
                        INSERT INTO memory_entries (
                            memory_type, niche, act_phase, persona_tone,
                            topic_keywords, bad_slide_text, human_gold_text,
                            why_it_works, burstiness_score, win_score, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item["memory_type"],
                            item["niche"],
                            item["act_phase"],
                            item["persona_tone"],
                            item["topic_keywords"],
                            item["bad_slide_text"],
                            item["human_gold_text"],
                            item["why_it_works"],
                            item["burstiness_score"],
                            item["win_score"],
                            now,
                        ),
                    )
            conn.commit()

    def add_memory(
        self,
        memory_type: str,
        niche: str,
        act_phase: str,
        human_gold_text: str,
        bad_slide_text: str = "",
        why_it_works: str = "",
        persona_tone: str = "cold_forensic",
        topic_keywords: str = "",
        burstiness_score: float = 8.5,
        win_score: float = 15.0,
    ) -> int:
        clean_gold = human_gold_text.strip()
        if not clean_gold:
            return -1
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not topic_keywords:
            topic_keywords = " ".join(re.findall(r"[A-Za-zÀ-ỹ]{4,}", clean_gold.lower())[:12])

        with self._connect() as conn:
            # Tránh lưu trùng lặp hoàn toàn cùng 1 câu
            dup = conn.execute(
                "SELECT id FROM memory_entries WHERE human_gold_text = ? LIMIT 1",
                (clean_gold,),
            ).fetchone()
            if dup:
                conn.execute(
                    "UPDATE memory_entries SET win_score = MIN(100.0, win_score + 1.5) WHERE id = ?",
                    (dup["id"],),
                )
                conn.commit()
                return int(dup["id"])

            cur = conn.execute(
                """
                INSERT INTO memory_entries (
                    memory_type, niche, act_phase, persona_tone,
                    topic_keywords, bad_slide_text, human_gold_text,
                    why_it_works, burstiness_score, win_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_type,
                    niche.lower(),
                    act_phase.upper(),
                    persona_tone,
                    topic_keywords,
                    bad_slide_text.strip(),
                    clean_gold,
                    why_it_works.strip(),
                    burstiness_score,
                    win_score,
                    now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def retrieve_context(
        self,
        niche: str,
        act_phase: str,
        query_text: str = "",
        top_k: int = 5,
    ) -> List[Dict]:
        """Truy xuất Hybrid (< 2ms): Kết hợp điểm BM25 của FTS5 + win_score + lọc theo Niche & Act Phase."""
        niche_clean = niche.lower().strip() or "general"
        phase_clean = act_phase.upper().strip() or "HOOK"
        fts_query = _sanitize_fts_query(query_text)

        rows: List[sqlite3.Row] = []
        with self._connect() as conn:
            if fts_query:
                try:
                    rows = conn.execute(
                        """
                        SELECT m.*,
                               (-bm25(memory_fts, 2.0, 1.5, 1.0) + m.win_score * 0.15 +
                                CASE WHEN m.niche = ? THEN 3.0 ELSE 0.0 END +
                                CASE WHEN m.act_phase = ? THEN 2.0 ELSE 0.0 END) AS rank_score
                        FROM memory_fts f
                        JOIN memory_entries m ON f.rowid = m.id
                        WHERE memory_fts MATCH ?
                          AND m.niche IN (?, 'general')
                        ORDER BY rank_score DESC
                        LIMIT ?
                        """,
                        (niche_clean, phase_clean, fts_query, niche_clean, top_k),
                    ).fetchall()
                except Exception:
                    rows = []

            if len(rows) < top_k:
                existing_ids = {r["id"] for r in rows}
                fallback_rows = conn.execute(
                    """
                    SELECT *,
                           (win_score * 0.15 +
                            CASE WHEN niche = ? THEN 4.0 ELSE 0.0 END +
                            CASE WHEN act_phase = ? THEN 3.0 ELSE 0.0 END) AS rank_score
                    FROM memory_entries
                    WHERE niche IN (?, 'general')
                    ORDER BY rank_score DESC
                    LIMIT ?
                    """,
                    (niche_clean, phase_clean, niche_clean, top_k * 2),
                ).fetchall()
                for fr in fallback_rows:
                    if fr["id"] not in existing_ids:
                        rows.append(fr)
                        existing_ids.add(fr["id"])
                    if len(rows) >= top_k:
                        break

        return [dict(r) for r in rows[:top_k]]

    def record_user_correction(self, old_slide_text: str, user_new_text: str, niche: str = "general", act_phase: str = "SETUP") -> int:
        """Ghi nhận câu do chính người dùng sửa tay trên giao diện UI với mức ưu tiên cao nhất (win_score = 100)."""
        return self.add_memory(
            memory_type="USER_FIX",
            niche=niche,
            act_phase=act_phase,
            bad_slide_text=old_slide_text,
            human_gold_text=user_new_text,
            why_it_works="Chỉnh sửa trực tiếp bởi Giám đốc sản xuất (User Override) — ưu tiên tuyệt đối văn phong này.",
            burstiness_score=9.8,
            win_score=100.0,
        )

    def learn_from_competitor_transcript(self, transcript: str, niche: str = "general", source_title: str = "") -> int:
        """Tự động đào các cặp câu có nhịp điệu người thật (câu hỏi tu từ, câu ngắn 3-6 từ đan xen câu dài) từ transcript đối thủ."""
        if not transcript or len(transcript) < 200:
            return 0
        raw_sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", transcript[:8000]) if s.strip()]
        if len(raw_sents) < 4:
            return 0

        learned = 0
        conversational_cues = (
            "except", "wait", "actually", "honestly", "reality", "problem", "truth",
            "nhưng", "thực tế", "khoan đã", "thế nhưng", "kỳ lạ",
        )
        for i in range(len(raw_sents) - 1):
            s1, s2 = raw_sents[i], raw_sents[i + 1]
            w1, w2 = len(s1.split()), len(s2.split())
            pair = f"{s1} {s2}"
            if re.search(r"\d", pair):
                continue
            # Nhịp câu người thật điển hình: 1 câu dài (12-24 từ) đi kèm 1 câu đinh cực ngắn (2-7 từ) hoặc có từ chuyển ý đời thực
            has_contrast_rhythm = (12 <= w1 <= 24 and 2 <= w2 <= 7) or (2 <= w1 <= 6 and 12 <= w2 <= 24)
            has_cue = any(k in pair.lower() for k in conversational_cues) or ("?" in pair)
            if has_contrast_rhythm and has_cue:
                phase = "HOOK" if i < 6 else "ESCALATION"
                self.add_memory(
                    memory_type="GOLDEN",
                    niche=niche,
                    act_phase=phase,
                    human_gold_text=pair,
                    why_it_works=f"Học tự động từ video '{source_title[:40]}': Nhịp câu tương phản ({w1} từ -> {w2} từ) tạo điểm nhấn tự nhiên.",
                    burstiness_score=9.1,
                    win_score=16.0,
                )
                learned += 1
                if learned >= 3:
                    break
        return learned

    def stats(self) -> Dict[str, int]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
            user_fixes = conn.execute("SELECT COUNT(*) FROM memory_entries WHERE memory_type = 'USER_FIX'").fetchone()[0]
            golden = conn.execute("SELECT COUNT(*) FROM memory_entries WHERE memory_type = 'GOLDEN'").fetchone()[0]
        return {"total_memories": total, "golden_patterns": golden, "user_fixes": user_fixes}
