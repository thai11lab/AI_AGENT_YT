"""Multi-Channel & Multi-Market Persona Registry (20 Kênh - 20 Ngách độc lập, chống trùng dấu vân tay âm thanh/hình ảnh)."""
from typing import Dict
from pydantic import BaseModel


class ChannelPersona(BaseModel):
    channel_id: str
    niche: str
    country_code: str = "US"
    market_lang: str = "en"
    tts_engine: str = "auto"
    kokoro_lang_code: str = "a"
    kokoro_voice: str = "am_adam"
    omnivoice_lang: str = "en"
    omnivoice_style_prompt: str = "male, middle-aged, low pitch"
    edge_voice: str = "en-US-AndrewNeural"
    openai_voice: str = "onyx"
    emotion_exaggeration: float = 0.72
    speaking_rate: str = "+8%"
    pitch_shift: str = "-3Hz"
    breath_pause_ms: int = 65
    emotion_prompt: str = (
        "Speak in a deep, gripping, investigative documentary narrator voice. "
        "Include natural breathing before revelations and sharp, deliberate pacing."
    )
    color_tint_hex: str = "#0c222e"
    accent_hex: str = "#38bdf8"
    voice_sample_path: str = ""


# =====================================================================
# BẢNG TÁCH GIỌNG NAM TRẦM THEO QUỐC GIA / THỊ TRƯỜNG (MULTI-COUNTRY MALE VOICES)
# =====================================================================
COUNTRY_VOICE_PACKS: Dict[str, Dict[str, str]] = {
    "US": {
        "name": "🇺🇸 Mỹ (American Documentary Baritone)",
        "market_lang": "en",
        "kokoro_lang_code": "a",
        "kokoro_voice": "am_adam",           # Ngoài ra có: am_fenrir, am_michael, am_onyx, am_echo, am_puck, am_liam
        "omnivoice_lang": "en",
        "omnivoice_style_prompt": "male, middle-aged, low pitch, american accent",
        "edge_voice": "en-US-AndrewNeural",
        "openai_voice": "onyx",
    },
    "UK": {
        "name": "🇬🇧 Anh Quốc (British BBC/Lemmino Cold Narrator)",
        "market_lang": "en",
        "kokoro_lang_code": "b",
        "kokoro_voice": "bm_george",         # Ngoài ra có: bm_lewis, bm_daniel, bm_fable
        "omnivoice_lang": "en",
        "omnivoice_style_prompt": "male, middle-aged, low pitch, british accent",
        "edge_voice": "en-GB-RyanNeural",
        "openai_voice": "fable",
    },
    "AU": {
        "name": "🇦🇺 Úc (Australian True-Crime / Survival Narrator)",
        "market_lang": "en",
        "kokoro_lang_code": "b",
        "kokoro_voice": "bm_lewis",
        "omnivoice_lang": "en",
        "omnivoice_style_prompt": "male, middle-aged, low pitch, australian accent",
        "edge_voice": "en-AU-WilliamNeural",
        "openai_voice": "ash",
    },
    "CA": {
        "name": "🇨🇦 Canada (North American Investigative Baritone)",
        "market_lang": "en",
        "kokoro_lang_code": "a",
        "kokoro_voice": "am_liam",
        "omnivoice_lang": "en",
        "omnivoice_style_prompt": "male, young adult, low pitch, canadian accent",
        "edge_voice": "en-CA-LiamNeural",
        "openai_voice": "echo",
    },
    "VN": {
        "name": "🇻🇳 Việt Nam - Giọng Nam Miền Bắc (Hà Nội Trầm Ấm - Kiểu VTV / Hồ Sơ Giải Mật)",
        "market_lang": "vi",
        "kokoro_lang_code": "a",
        "kokoro_voice": "am_adam",
        "omnivoice_lang": "vi",
        "omnivoice_style_prompt": "male, middle-aged, very low pitch",
        "edge_voice": "vi-VN-NamMinhNeural",
        "openai_voice": "onyx",
        "voice_sample_path": "voices/vn_male_north_hanoi.wav",
    },
    "VN_BAC": {
        "name": "🇻🇳 Việt Nam - Giọng Nam Miền Bắc Chuẩn (Hà Nội - Phát Thanh Viên Điều Tra)",
        "market_lang": "vi",
        "kokoro_lang_code": "a",
        "kokoro_voice": "am_adam",
        "omnivoice_lang": "vi",
        "omnivoice_style_prompt": "male, middle-aged, very low pitch",
        "edge_voice": "vi-VN-NamMinhNeural",
        "openai_voice": "onyx",
        "voice_sample_path": "voices/vn_male_north_hanoi.wav",
    },
    "VN_NAM": {
        "name": "🇻🇳 Việt Nam - Giọng Nam Miền Nam (Sài Gòn Trầm Ấm - Kể Chuyện Đời Thường)",
        "market_lang": "vi",
        "kokoro_lang_code": "a",
        "kokoro_voice": "am_adam",
        "omnivoice_lang": "vi",
        "omnivoice_style_prompt": "male, young adult, moderate pitch",
        "edge_voice": "vi-VN-NamMinhNeural",
        "openai_voice": "echo",
        "voice_sample_path": "voices/vn_male_south_saigon.wav",
    },
    "JP": {
        "name": "🇯🇵 Nhật Bản (Japanese Deep Investigative Male)",
        "market_lang": "ja",
        "kokoro_lang_code": "j",
        "kokoro_voice": "jm_kumo",
        "omnivoice_lang": "ja",
        "omnivoice_style_prompt": "male, middle-aged, low pitch, japanese accent",
        "edge_voice": "ja-JP-KeitaNeural",
        "openai_voice": "onyx",
    },
    "FR": {
        "name": "🇫🇷 Pháp (French Investigative Documentary Male)",
        "market_lang": "fr",
        "kokoro_lang_code": "f",
        "kokoro_voice": "ff_siwis",
        "omnivoice_lang": "fr",
        "omnivoice_style_prompt": "male, middle-aged, low pitch",
        "edge_voice": "fr-FR-HenriNeural",
        "openai_voice": "onyx",
    },
    "ES": {
        "name": "🇪🇸 Tây Ban Nha / LatAm (Spanish Documentary Male)",
        "market_lang": "es",
        "kokoro_lang_code": "e",
        "kokoro_voice": "em_alex",
        "omnivoice_lang": "es",
        "omnivoice_style_prompt": "male, middle-aged, low pitch",
        "edge_voice": "es-ES-AlvaroNeural",
        "openai_voice": "onyx",
    },
}


CHANNEL_PRESETS: Dict[str, ChannelPersona] = {
    "ch01_med_forensic": ChannelPersona(
        channel_id="ch01_med_forensic", niche="01. Dark Medical & Bio-Forensics",
        kokoro_voice="am_adam", edge_voice="en-US-AndrewNeural", openai_voice="onyx", emotion_exaggeration=0.75,
        speaking_rate="+8%", pitch_shift="-2Hz", color_tint_hex="#0c222e", accent_hex="#38bdf8",
    ),
    "ch02_cyber_heist": ChannelPersona(
        channel_id="ch02_cyber_heist", niche="02. Cyber-Crime & Darknet Heists",
        kokoro_voice="am_michael", edge_voice="en-US-ChristopherNeural", openai_voice="echo", emotion_exaggeration=0.78,
        speaking_rate="+10%", pitch_shift="-4Hz", color_tint_hex="#091e1a", accent_hex="#10b981",
    ),
    "ch03_corp_fraud": ChannelPersona(
        channel_id="ch03_corp_fraud", niche="03. Corporate Fraud & Dirty Money",
        kokoro_voice="am_fenrir", edge_voice="en-US-EricNeural", openai_voice="onyx", emotion_exaggeration=0.80,
        speaking_rate="+9%", pitch_shift="-3Hz", color_tint_hex="#1a120b", accent_hex="#f59e0b",
    ),
    "ch04_aviation_disaster": ChannelPersona(
        channel_id="ch04_aviation_disaster", niche="04. Aviation & Maritime Disasters",
        kokoro_voice="bm_george", edge_voice="en-GB-RyanNeural", openai_voice="ash", emotion_exaggeration=0.68,
        speaking_rate="+5%", pitch_shift="-4Hz", color_tint_hex="#111827", accent_hex="#ef4444",
    ),
    "ch05_true_crime": ChannelPersona(
        channel_id="ch05_true_crime", niche="05. True Crime & Interrogation Psychology",
        kokoro_voice="bm_lewis", edge_voice="en-AU-WilliamNeural", openai_voice="fable", emotion_exaggeration=0.76,
        speaking_rate="+4%", pitch_shift="-5Hz", color_tint_hex="#220d14", accent_hex="#f43f5e",
    ),
    "ch06_geopolitics": ChannelPersona(
        channel_id="ch06_geopolitics", niche="06. Geopolitics, Espionage & Shadow Wars",
        kokoro_voice="bm_george", edge_voice="en-GB-ThomasNeural", openai_voice="onyx", emotion_exaggeration=0.70,
        speaking_rate="+7%", pitch_shift="-3Hz", color_tint_hex="#18181b", accent_hex="#eab308",
    ),
    "ch07_deep_space": ChannelPersona(
        channel_id="ch07_deep_space", niche="07. Space Anomalies & Deep Cosmos",
        kokoro_voice="am_echo", edge_voice="en-US-BrianNeural", openai_voice="alloy", emotion_exaggeration=0.66,
        speaking_rate="+3%", pitch_shift="-4Hz", color_tint_hex="#090d24", accent_hex="#818cf8",
    ),
    "ch08_ai_future": ChannelPersona(
        channel_id="ch08_ai_future", niche="08. AI Singularity & Frontier Tech",
        kokoro_voice="am_puck", edge_voice="en-US-SteffanNeural", openai_voice="echo", emotion_exaggeration=0.74,
        speaking_rate="+11%", pitch_shift="-1Hz", color_tint_hex="#0d1b2a", accent_hex="#06b6d4",
    ),
    "ch09_ancient_mystery": ChannelPersona(
        channel_id="ch09_ancient_mystery", niche="09. Ancient Civilizations & Archaeology",
        kokoro_voice="bm_daniel", edge_voice="en-GB-RyanNeural", openai_voice="fable", emotion_exaggeration=0.70,
        speaking_rate="+4%", pitch_shift="-5Hz", color_tint_hex="#261c14", accent_hex="#d97706",
    ),
    "ch10_dark_psych": ChannelPersona(
        channel_id="ch10_dark_psych", niche="10. Dark Psychology, Cults & Social Experiments",
        kokoro_voice="am_onyx", edge_voice="en-US-RogerNeural", openai_voice="onyx", emotion_exaggeration=0.77,
        speaking_rate="+6%", pitch_shift="-4Hz", color_tint_hex="#1e112a", accent_hex="#c084fc",
    ),
    "ch11_extreme_survival": ChannelPersona(
        channel_id="ch11_extreme_survival", niche="11. Extreme Survival & Vanished Expeditions",
        kokoro_voice="am_liam", edge_voice="en-CA-LiamNeural", openai_voice="ash", emotion_exaggeration=0.79,
        speaking_rate="+8%", pitch_shift="-3Hz", color_tint_hex="#0f241d", accent_hex="#34d399",
    ),
    "ch12_megaprojects": ChannelPersona(
        channel_id="ch12_megaprojects", niche="12. Billionaire Megaprojects & Engineering",
        kokoro_voice="am_michael", edge_voice="en-US-GuyNeural", openai_voice="echo", emotion_exaggeration=0.72,
        speaking_rate="+9%", pitch_shift="-2Hz", color_tint_hex="#102027", accent_hex="#fbbf24",
    ),
    "ch13_military_black": ChannelPersona(
        channel_id="ch13_military_black", niche="13. Classified Weapons & Military Black Projects",
        kokoro_voice="am_fenrir", edge_voice="en-US-EricNeural", openai_voice="onyx", emotion_exaggeration=0.75,
        speaking_rate="+8%", pitch_shift="-5Hz", color_tint_hex="#141e14", accent_hex="#84cc16",
    ),
    "ch14_sports_scandal": ChannelPersona(
        channel_id="ch14_sports_scandal", niche="14. Sports Scandals, Doping & High-Stakes Betrayal",
        kokoro_voice="am_adam", edge_voice="en-US-AndrewNeural", openai_voice="alloy", emotion_exaggeration=0.82,
        speaking_rate="+12%", pitch_shift="-2Hz", color_tint_hex="#24140e", accent_hex="#fb923c",
    ),
    "ch15_virtual_economy": ChannelPersona(
        channel_id="ch15_virtual_economy", niche="15. Gaming Lore, Speedrun Cheats & Virtual Heists",
        kokoro_voice="am_puck", edge_voice="en-US-BrianNeural", openai_voice="echo", emotion_exaggeration=0.78,
        speaking_rate="+11%", pitch_shift="-1Hz", color_tint_hex="#151028", accent_hex="#a78bfa",
    ),
    "ch16_food_monopoly": ChannelPersona(
        channel_id="ch16_food_monopoly", niche="16. Food Cartels, Supply Chain & Consumer Deception",
        kokoro_voice="am_michael", edge_voice="en-US-SteffanNeural", openai_voice="ash", emotion_exaggeration=0.74,
        speaking_rate="+8%", pitch_shift="-3Hz", color_tint_hex="#1f1d0e", accent_hex="#facc15",
    ),
    "ch17_hollywood_dark": ChannelPersona(
        channel_id="ch17_hollywood_dark", niche="17. Entertainment Industry & Billion-Dollar Feuds",
        kokoro_voice="am_adam", edge_voice="en-US-AndrewNeural", openai_voice="onyx", emotion_exaggeration=0.76,
        speaking_rate="+9%", pitch_shift="-2Hz", color_tint_hex="#260f1e", accent_hex="#f472b6",
    ),
    "ch18_deep_ocean": ChannelPersona(
        channel_id="ch18_deep_ocean", niche="18. Deep Ocean, Antarctica & Extreme Earth",
        kokoro_voice="bm_george", edge_voice="en-GB-RyanNeural", openai_voice="onyx", emotion_exaggeration=0.69,
        speaking_rate="+5%", pitch_shift="-4Hz", color_tint_hex="#071926", accent_hex="#22d3ee",
    ),
    "ch19_crypto_forensics": ChannelPersona(
        channel_id="ch19_crypto_forensics", niche="19. Crypto Rugpulls, On-Chain Forensics & Casinos",
        kokoro_voice="am_fenrir", edge_voice="en-US-ChristopherNeural", openai_voice="echo", emotion_exaggeration=0.81,
        speaking_rate="+11%", pitch_shift="-3Hz", color_tint_hex="#181226", accent_hex="#f59e0b",
    ),
    "ch20_dieu_tra_vn": ChannelPersona(
        channel_id="ch20_dieu_tra_vn", niche="20. Hồ Sơ Giải Mật & Điều Tra (Việt Nam - Giọng Nam Miền Bắc)",
        country_code="VN_BAC", market_lang="vi", kokoro_voice="am_adam",
        omnivoice_lang="vi",
        omnivoice_style_prompt="male, middle-aged, very low pitch",
        edge_voice="vi-VN-NamMinhNeural", openai_voice="onyx", emotion_exaggeration=0.74,
        speaking_rate="+6%", pitch_shift="-3Hz", color_tint_hex="#111827", accent_hex="#f59e0b",
        voice_sample_path="voices/vn_male_north_hanoi.wav",
    ),
    # Giữ tương thích ngược với 5 mã cũ
    "med_forensic_us": ChannelPersona(
        channel_id="med_forensic_us", niche="Medical & Bioethics Mysteries",
        edge_voice="en-US-AndrewNeural", openai_voice="onyx", emotion_exaggeration=0.75,
        speaking_rate="+8%", pitch_shift="-2Hz", color_tint_hex="#0c222e", accent_hex="#38bdf8",
    ),
    "dark_history_uk": ChannelPersona(
        channel_id="dark_history_uk", niche="Declassified History & Intelligence",
        edge_voice="en-GB-RyanNeural", openai_voice="ash", emotion_exaggeration=0.68,
        speaking_rate="+5%", pitch_shift="-4Hz", color_tint_hex="#1f1912", accent_hex="#f59e0b",
    ),
    "finance_crime_us": ChannelPersona(
        channel_id="finance_crime_us", niche="Wall Street Frauds & Corporate Collapse",
        edge_voice="en-US-EricNeural", openai_voice="echo", emotion_exaggeration=0.78,
        speaking_rate="+9%", pitch_shift="-3Hz", color_tint_hex="#0e1f18", accent_hex="#10b981",
    ),
    "true_crime_au": ChannelPersona(
        channel_id="true_crime_au", niche="Cold Case Forensics",
        edge_voice="en-AU-WilliamNeural", openai_voice="fable", emotion_exaggeration=0.75,
        speaking_rate="+5%", pitch_shift="-4Hz", color_tint_hex="#241016", accent_hex="#ef4444",
    ),
    "dieu_tra_vn": ChannelPersona(
        channel_id="dieu_tra_vn", niche="Hồ Sơ Giải Mật & Pháp Y (Việt Nam)",
        market_lang="vi", edge_voice="vi-VN-NamMinhNeural", openai_voice="onyx", emotion_exaggeration=0.70,
        speaking_rate="+6%", pitch_shift="-3Hz", color_tint_hex="#111827", accent_hex="#f59e0b",
    ),
    "gta_mystery": ChannelPersona(
        channel_id="gta_mystery", niche="GTA V / VI Lore, Easter Eggs & Los Santos Mysteries",
        country_code="VN_BAC", market_lang="vi", kokoro_voice="am_puck",
        omnivoice_lang="vi", omnivoice_style_prompt="male, young adult, moderate pitch",
        edge_voice="vi-VN-NamMinhNeural", openai_voice="echo", emotion_exaggeration=0.80,
        speaking_rate="+8%", pitch_shift="-2Hz", color_tint_hex="#151028", accent_hex="#a78bfa",
    ),
}


def get_channel_persona(channel_id: str, lang: str = "en", country: str = "") -> ChannelPersona:
    base = CHANNEL_PRESETS.get(channel_id)
    if not base:
        base = CHANNEL_PRESETS["ch20_dieu_tra_vn"] if lang == "vi" else CHANNEL_PRESETS["ch01_med_forensic"]
    if not country:
        return base
    c_key = country.upper().strip()
    if c_key not in COUNTRY_VOICE_PACKS:
        return base
    pack = COUNTRY_VOICE_PACKS[c_key]
    cloned = base.model_copy(deep=True)
    cloned.country_code = c_key
    cloned.market_lang = pack["market_lang"]
    cloned.kokoro_lang_code = pack["kokoro_lang_code"]
    cloned.kokoro_voice = pack["kokoro_voice"]
    cloned.omnivoice_lang = pack["omnivoice_lang"]
    cloned.omnivoice_style_prompt = pack["omnivoice_style_prompt"]
    cloned.edge_voice = pack["edge_voice"]
    cloned.openai_voice = pack["openai_voice"]
    if pack.get("voice_sample_path"):
        cloned.voice_sample_path = pack["voice_sample_path"]
    return cloned
