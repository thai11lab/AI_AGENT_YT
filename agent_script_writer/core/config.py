import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

RUN_BUDGET = {"max_usd": 1.20, "max_minutes": 25, "max_hunter_calls": 24, "max_scrape_pages": 40}

# Mặc định toàn bộ dùng Gemini (free tier). Ghi đè bằng biến môi trường nếu cần.
MODELS = {
    "autopsy": os.getenv("MODEL_AUTOPSY", "gemini-3.5-flash"),
    "architect": os.getenv("MODEL_ARCHITECT", "gemini-3.5-flash"),
    "hunter": os.getenv("MODEL_HUNTER", "gemini-3.5-flash"),
    "prosecutor": os.getenv("MODEL_PROSECUTOR", "gemini-3.5-flash"),
    "writer": os.getenv("MODEL_WRITER", "gemini-3.5-flash"),
}

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()


def get_key(name: str, required: bool = True) -> str:
    v = os.getenv(name, "").strip()
    if required and not v:
        raise RuntimeError(f"Thiếu {name} trong {ROOT / '.env'}")
    return v
